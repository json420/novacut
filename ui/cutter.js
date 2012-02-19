"use strict";

var Thumbs = {
    db: new couch.Database('thumbnails'), 

    docs: {},

    has_frame: function(file_id, index) {
        if (!Thumbs.docs[file_id]) {
            try {
                Thumbs.docs[file_id] = Thumbs.db.get_sync(file_id);
            }
            catch (e) {
                return false;
            }
        }
        if (Thumbs.docs[file_id]._attachments[index]) {
            return true;
        }
        return false;
    },

    q: {},

    init: function() {
        var ids = Object.keys(Thumbs.q);
        if (ids.length == 0) {
            return;
        }
        Thumbs.db.post(Thumbs.on_docs, {keys: ids}, '_all_docs', {include_docs: true});
    },

    on_docs: function(req) {
        try {
            var rows = req.read().rows;
            rows.forEach(function(row) {
                var id = row.key;
                if (row.doc) {
                    Thumbs.docs[id] = row.doc;
                }
                else {
                    Thumbs.docs[id] = {'_id': id, '_attachments': {}};
                }
            });
        }
        catch (e) {
            var ids = Object.keys(Thumbs.q);
            ids.forEach(function(id) {
                Thumbs.docs[id] = {'_id': id, '_attachments': {}};
            });
        }
        Thumbs.flush();
    },

    enqueue: function(frame) {
        if (!Thumbs.q[frame.file_id]) {
            Thumbs.q[frame.file_id] = [];
        }
        Thumbs.q[frame.file_id].push(frame);
    },

    flush: function() {
        var ids = Object.keys(Thumbs.q);
        if (ids.length == 0) {
            return;
        }
        ids.forEach(function(id) {
            var frames = Thumbs.q[id];
            var needed = [];
            frames.forEach(function(frame) {
                if (Thumbs.has_frame(id, frame.index)) {
                    frame.request_thumbnail.call(frame);
                }
                else {
                    needed.push(frame.index);
                }
            });
            if (needed.length == 0) {
                delete Thumbs.q[id];
            }
            else {
                Hub.send('thumbnail', id, needed);
            }
        }); 
    },

    on_thumbnail_finished: function(file_id) {
        if (!Thumbs.q[file_id]) {
            return;
        }
        var frames = Thumbs.q[file_id];
        delete Thumbs.q[file_id];
        Thumbs.docs[file_id] = Thumbs.db.get_sync(file_id);
        frames.forEach(function(frame) {
            if (Thumbs.has_frame(file_id, frame.index)) {
                frame.request_thumbnail.call(frame);
            }
            else {
                Thumbs.enqueue(frame);
            }
        });
        Thumbs.flush();
    },
}

Hub.connect('thumbnail_finished', Thumbs.on_thumbnail_finished);


var Frame = function(file_id) {
    this.file_id = file_id;
    this.index = null;
    this.element = $el('div', {'class': 'frame'});
    this.img = $el('img');
    this.element.appendChild(this.img);
    this.info = $el('div');
    this.element.appendChild(this.info);
}
Frame.prototype = {
    set_index: function(index) {
        if (index === this.index) {
            return;
        }
        this.index = index;
        this.info.textContent = index + 1;
        Thumbs.enqueue(this);
    },

    request_thumbnail: function() {
        this.img.src = Thumbs.db.att_url(this.file_id, this.index.toString());
    },

}


function wheel_delta(event) {
    var delta = event.wheelDeltaY;
    if (delta == 0) {
        return 0;
    }
    var scale = (event.shiftKey) ? -10 : -1;
    return scale * (delta / Math.abs(delta));
}


function SliceIndicator() {
    this.element = $el('div', {'class': 'indicator'});
    this.bar = $el('div');
    this.element.appendChild(this.bar);
}
SliceIndicator.prototype = {
    update: function(start, stop, count) {
        var left = 100 * start / count;
        var right = 100 - (100 * stop / count);
        this.bar.style.left = left.toFixed(1) + '%';
        this.bar.style.right = right.toFixed(1) + '%';  
    },
}


function $halt(event) {
    event.preventDefault();
    event.stopPropagation();
}


function $unparent(id) {
    var child = $(id);
    if (child && child.parentNode) {
        child.parentNode.removeChild(child);
    }
    return child;
}


function $swap(a, b) {
    var a_dummy = document.createElement('div');
    var b_dummy = document.createElement('div');
    var a = $replace(a, a_dummy);
    var b = $replace(b, b_dummy);
    $replace(a_dummy, b);
    $replace(b_dummy, a);
}


var Slice = function(session, doc) {
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.element = $el('div', {'class': 'slice', 'id': doc._id});

    this.count = session.get_doc(doc.node.src).duration.frames;

    var src = doc.node.src;
    this.start = new Frame(src);
    this.element.appendChild(this.start.element);

    //this.indicator = new SliceIndicator();
    //this.element.appendChild(this.indicator.element);

    this.end = new Frame(src);
    this.element.appendChild(this.end.element);

    this.on_change(doc, true);

    var self = this;
    this.start.element.onmousewheel = function(event) {
        self.on_mousewheel_start(event);
    }
    this.end.element.onmousewheel = function(event) {
        self.on_mousewheel_end(event);
    }

    this.grabbed = false;
    this.element.onmousedown = function(e) {
        return self.on_mousedown(e);
    }
    this.size = 192;
    this.threshold = this.size * 0.6;
}
Slice.prototype = {
    on_mousewheel_start: function(event) {
        event.preventDefault();
        event.stopPropagation();
        var delta = wheel_delta(event);
        var start = this.doc.node.start.frame;
        var stop = this.doc.node.stop.frame;
        var proposed = Math.max(0, Math.min(start + delta, stop - 1));
        if (start != proposed) {
            this.doc.node.start.frame = proposed;
            this.session.save(this.doc);
            this.session.commit();
        }   
    },

    on_mousewheel_end: function(event) {
        event.preventDefault();
        event.stopPropagation();
        var delta = wheel_delta(event);
        var start = this.doc.node.start.frame;
        var stop = this.doc.node.stop.frame;
        var proposed = Math.max(start + 1, Math.min(stop + delta, this.count));
        if (stop != proposed) {
            this.doc.node.stop.frame = proposed;
            this.session.save(this.doc);
            this.session.commit();
        }   
    },

    on_change: function(doc, no_flush) {
        this.doc = doc;
        var node = doc.node;
        //this.indicator.update(node.start.frame, node.stop.frame, this.count);
        this.start.set_index(node.start.frame);
        this.end.set_index(node.stop.frame - 1);
        if (!no_flush) {
            Thumbs.flush();
        }
    },
    
    set x(value) {
        if (value === null) {
            this.element.style.left = null;
        }
        else {
            this.element.style.left = value + 'px';
        }
    },

    set y(value) {
        if (value === null) {
            this.element.style.top = null;
        }
        else {
            this.element.style.top = value + 'px';
        }
    },

    grab: function() {
        this.grabbed = true;
        this.target = this.element;
        this.pos = 0;
        this.x = 0;
        var children = Array.prototype.slice.call(this.element.parentNode.children);
        children.forEach(function(child) {
            child.classList.remove('home');
        });
        this.element.classList.add('grabbed');
    },

    ungrab: function() {
        console.log('ungrab');
        this.grabbed = false;
        this.x = null;
        this.element.classList.add('home');
        this.element.classList.remove('grabbed');
        var children = Array.prototype.slice.call(this.element.parentNode.children);
        children.forEach(function(child) {
            child.classList.remove('right');
            child.classList.remove('left');
            child.classList.remove('neutral');
        });
    },

    on_mousedown: function(event) {
        $halt(event);
        var self = this;
        var tmp = {};
        tmp.on_mousemove = function(event) {
            self.on_mousemove(event);
        }
        tmp.on_mouseup = function(event) {
            self.ungrab();
            window.removeEventListener('mousemove', tmp.on_mousemove);
            window.removeEventListener('mouseup', tmp.on_mouseup);
        }
        window.addEventListener('mousemove', tmp.on_mousemove);
        window.addEventListener('mouseup', tmp.on_mouseup);
        this.orig_x = event.screenX;
        this.grab();
    },

    on_mouseout: function(e) {
        console.log('mouseout');
        if (this.grabbed === true) {
            this.ungrab();
        }
    },

    on_mousemove: function(event) {
        $halt(event);
        var dx = event.screenX - this.orig_x;
        this.x = dx;
        var rdx = dx - (this.size * this.pos);
        if (rdx < -this.threshold) {
            this.shift_right();
        }
        else if (rdx > this.threshold) {
            this.shift_left();
        }
    },

    shift_right: function() {
        if (!this.target.previousSibling) {
            return;
        }
        this.pos -= 1;
        if (this.target.classList.contains('left')) {
            this.target.classList.add('neutral');
            this.target.classList.remove('left');
        }
        else {
            this.target.previousSibling.classList.add('right');
            this.target.previousSibling.classList.remove('neutral');
        }
        this.target = this.target.previousSibling;
    },

    shift_left: function() {
        if (!this.target.nextSibling) {
            return;
        }
        this.pos += 1;
        if (this.target.classList.contains('right')) {
            this.target.classList.add('neutral');
            this.target.classList.remove('right');
        }
        else {
            this.target.nextSibling.classList.add('left');
            this.target.nextSibling.classList.remove('neutral');
        }
        this.target = this.target.nextSibling;

    },
    
}


var Sequence = function(session, doc) {
    this.element = $el('div', {'class': 'sequence', 'id': doc._id});
    //this.items = new Items(this.element);
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.on_change(doc);
    this.element.onmousewheel = $bind(this.on_mousewheel, this);

    this.element.ondragenter = $bind(this.on_dragenter, this);
    this.element.ondragover = $bind(this.on_dragover, this);
    this.element.ondrop = $bind(this.on_drop, this);
}
Sequence.prototype = {
    on_change: function(doc) {
        this.doc = doc;
        var self = this;
        doc.node.src.forEach(function(_id) {
            var slice = new Slice(this.session, this.session.get_doc(_id));
//            slice.element.onclick = function() {
//                self.items.select(_id);
//            }
            this.append(slice);
        }, this);
        Thumbs.flush();
    },

    append: function(child) {
        this.element.appendChild(child.element);
    },

    on_mousewheel: function(event) {
        $halt(event);
        var delta = wheel_delta(event) * 194;  // 192px width + 1px border
        this.element.scrollLeft += delta;
    },

    on_dragenter: function(event) {
        event.preventDefault();
    },

    on_dragover: function(event) {
        event.preventDefault();
    },

    on_drop: function(event) {
        var _id = event.dataTransfer.getData('text/plain');
        console.log(['drop', _id].join(' '));
    } 
}


var UI = {
    init: function() {
        var id = window.location.hash.slice(1);
        var doc = novacut.get_sync(id);
        UI.db = new couch.Database(doc.db_name);
        UI.project = UI.db.get_sync(id);

        set_title('title', UI.project.title);
        UI.session = new couch.Session(UI.db, UI.on_new_doc);
        UI.session.start();

    },

    on_new_doc: function(doc) {
        if (doc._id == UI.project.root_id) {
            UI.sequence = new Sequence(UI.session, doc);
            document.body.appendChild(UI.sequence.element);
        }
    },
}

window.addEventListener('load', UI.init);

Hub.connect('render_finished',
    function(job_id, file_id) {
        var player = $('player');
        player.src = 'dmedia:' + file_id;
        player.play();
    }
);
