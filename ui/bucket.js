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

    active: {},

    need_init: true,

    init: function() {
        console.assert(Thumbs.need_init);
        Thumbs.need_init = false;
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
        Thumbs.unfreeze();
    },

    enqueue: function(frame) {
        if (!Thumbs.q[frame.file_id]) {
            Thumbs.q[frame.file_id] = {};
        }
        Thumbs.q[frame.file_id][frame.key] = frame;
    },
    
    frozen: false,

    freeze: function() {
        Thumbs.frozen = true;
    },
    
    unfreeze: function() {
        console.log('unfreeze');
        if (this.need_init) {
            this.init();
            return;
        }
        Thumbs.frozen = false;
        Thumbs.flush();
    },

    flush: function() {
        if (Thumbs.frozen) {
            return;
        }
        var ids = Object.keys(Thumbs.q);
        if (ids.length == 0) {
            console.log('no thumbnails in queue');
            return;
        }
        while (ids.length > 0 && Object.keys(Thumbs.active).length <= 4) {
            var id = ids.shift();
            if (Thumbs.active[id]) {
                console.log('already waiting for ' + id);
                continue;
            }
            var frames = Thumbs.q[id];
            delete Thumbs.q[id];

            var needed = [];
            var key, frame;
            for (key in frames) {
                frame = frames[key];
                if (Thumbs.has_frame(id, frame.index)) {
                    frame.request_thumbnail.call(frame);
                }
                else {
                    needed.push(frame.index);
                }
            }
            if (needed.length > 0) {
                Thumbs.active[id] = frames;
                Hub.send('thumbnail', id, needed);
            }
        }
    },

    on_thumbnail_finished: function(file_id) {
        if (!Thumbs.active[file_id]) {
            return;
        }
        var frames = Thumbs.active[file_id];
        delete Thumbs.active[file_id];
        Thumbs.docs[file_id] = Thumbs.db.get_sync(file_id);
        
        var key, frame;
        for (key in frames) {
            frame = frames[key];
            if (Thumbs.has_frame(file_id, frame.index)) {
                frame.request_thumbnail.call(frame);
            }
        }
        Thumbs.flush();
    },
}

Hub.connect('thumbnail_finished', Thumbs.on_thumbnail_finished);


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


function $position(element) {
    var pos = {
        left: element.offsetLeft,
        top: element.offsetTop,
        width: element.offsetWidth,
        height: element.offsetHeight,
    };
    while (element.offsetParent) {
        element = element.offsetParent;
        pos.left += (element.offsetLeft - element.scrollLeft);
        pos.top += (element.offsetTop - element.scrollTop);
    }
    pos.right = pos.left + pos.width;
    pos.bottom = pos.top + pos.height;
    return pos;
}


var DragEvent = function(event, element) {
    $halt(event);
    this.x = event.clientX;
    this.y = event.clientY;
    this.ox = this.x;
    this.oy = this.y;
    this.dx = 0;
    this.dy = 0;
    
    if (element) {
        var pos = $position(element);
        this.offsetX = this.x - pos.left;
        this.offsetY = this.y - pos.top;
    }
    else {    
        this.offsetX = event.offsetX;
        this.offsetY = event.offsetY;
    }

    this.ondragstart = null;
    this.ondragcancel = null;
    this.ondrag = null;
    this.ondrop = null;
    this.started = false;

    var self = this;
    var tmp = {};
    tmp.on_mousemove = function(event) {
        self.on_mousemove(event);            
    }
    tmp.on_mouseup = function(event) {
        window.removeEventListener('mousemove', tmp.on_mousemove);
        window.removeEventListener('mouseup', tmp.on_mouseup);
        self.on_mouseup(event);
    }
    window.addEventListener('mousemove', tmp.on_mousemove);
    window.addEventListener('mouseup', tmp.on_mouseup);
}
DragEvent.prototype = {
    update: function(event) {
        $halt(event);
        this.event = event;
        var html = document.body.parentNode;
        this.x = Math.max(0, Math.min(event.clientX, html.clientWidth));
        this.y = Math.max(0, Math.min(event.clientY, html.clientHeight));
//        this.x = event.clientX;
//        this.y = event.clientY;
        this.dx = this.x - this.ox;
        this.dy = this.y - this.oy;
    },

    on_mousemove: function(event) {
        this.update(event);
        if (!this.started) {
            if (Math.max(Math.abs(this.dx), Math.abs(this.dy)) > 3) {
                this.started = true;
                if (this.ondragstart) {
                    this.ondragstart(this);
                }   
            }
            else {
                return;
            }
        }
        if (this.ondrag) {
            this.ondrag(this);
        }
    },

    on_mouseup: function(event) {
        if (!this.started) {
            if (this.ondragcancel) {
                this.ondragcancel(this);
            }
            return;
        }
        if (this.ondrop) {
            this.update(event);
            this.ondrop(this);
        }
    },
}


var Frame = function(file_id, key) {
    this.file_id = file_id;
    this.key = key;
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


function wheel_delta(event) {
    var delta = event.wheelDeltaY;
    if (delta == 0) {
        return 0;
    }
    var scale = (event.shiftKey) ? -10 : -1;
    return scale * (delta / Math.abs(delta));
}


var Slice = function(session, doc) {
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.element = $el('div', {'class': 'slice', 'id': doc._id});

    var file_id = doc.node.src;

    this.start = new Frame(file_id, doc._id + '.start');
    this.element.appendChild(this.start.element);
    
    this.indicator = new SliceIndicator();
    this.element.appendChild(this.indicator.element);

    this.end = new Frame(file_id, doc._id + '.end');
    this.element.appendChild(this.end.element);

    this.start.element.onmousewheel = $bind(this.on_mousewheel_start, this);
    this.end.element.onmousewheel = $bind(this.on_mousewheel_end, this);
    this.element.onmousedown = $bind(this.on_mousedown, this);
    this.element.ondblclick = $bind(this.on_dblclick, this);

    this.frames = session.get_doc(doc.node.src).duration.frames;
    this.on_change(doc);

    this.i = null;
    this.over = null;
    this.width = 192 + 2;
    this.threshold = this.width * 0.65;
    
}
Slice.prototype = {
    set x(value) {
        if (typeof value == 'number') {
            this.element.style.left = value + 'px';
        }
        else {
            this.element.style.left = null;
        }
    },

    set y(value) {
        if (typeof value == 'number') {
            this.element.style.top = value + 'px';
        }
        else {
            this.element.style.top = null;
        }
    },

    get x() {
        return parseInt(this.element.style.left);
    },

    get y() {
        return parseInt(this.element.style.top);
    },

    get inbucket() {
        return this.element.parentNode.id == 'bucket';
    },

    get frombucket() {
        return this.parent.id == 'bucket';
    },

    on_change: function(doc) {
        this.doc = doc;
        var node = doc.node;
        this.start.set_index(node.start.frame);
        this.end.set_index(node.stop.frame - 1);
        this.indicator.update(node.start.frame, node.stop.frame, this.frames);
        Thumbs.flush();
    },

    on_mousewheel_start: function(event) {
        $halt(event);
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
        $halt(event);
        var delta = wheel_delta(event);
        var start = this.doc.node.start.frame;
        var stop = this.doc.node.stop.frame;
        var proposed = Math.max(start + 1, Math.min(stop + delta, this.frames));
        if (stop != proposed) {
            this.doc.node.stop.frame = proposed;
            this.session.save(this.doc);
            this.session.commit();
        }   
    },

    on_mousedown: function(event) {
        UI.select(this.element);
        this.pos = $position(this.element);
        this.dnd = new DragEvent(event, this.element);
        this.dnd.ondragcancel = $bind(this.on_dragcancel, this);
        this.dnd.ondragstart = $bind(this.on_dragstart, this);
        this.dnd.ondrag = $bind(this.on_drag, this);
        this.dnd.ondrop = $bind(this.on_drop, this);
    },

    on_dblclick: function(event) {
        $halt(event);
        UI.edit_slice(this.doc);
    },

    on_dragcancel: function(dnd) {
        console.log('dragcancel');
        this.stop_scrolling();
        if (this.inbucket && UI.bucket.lastChild != this.element) {
            console.log('moving to end of bucket');
            $unparent(this.element);
            UI.bucket.appendChild(this.element);
            UI.sequence.do_reorder();
        }
        else if (UI.sequence.doc.selected != this.element.id) {
            console.log('updating selected element');
            UI.sequence.do_reorder();
        }
    },

    on_dragstart: function(dnd) {
        console.log('dragstart');
        this.offsetX = this.dnd.offsetX;
        this.offsetY = this.dnd.offsetY;
        this.offsetWidth = this.element.offsetWidth;
        this.offsetHeight = this.element.offsetHeight;

        this.parent = this.element.parentNode;
        this.x = dnd.x - this.offsetX;
        if (this.inbucket) {
            this.y = dnd.y - this.offsetY;
        }
        else {
            this.nextSibling = this.element.nextSibling;
            if (this.element.nextSibling) {
                this.over = this.element.nextSibling;
                this.over.classList.add('over'); 
            }
            else if (this.element.previousSibling) {
                this.over = this.element.previousSibling;
                this.over.classList.add('over-right'); 
            }
            this.target = this.element;
            var seq = this.element.parentNode;
            var i, child;
            for (i=0; i<seq.children.length; i++) {
                child = seq.children[i];
                if (child == this.element) {
                    this.i = i;
                    this.orig_i = i;
                }
            }
            this.y = UI.sequence.top - 14;
        }
        this.element.classList.add('grabbed');
    },

    on_drag: function(dnd) {
        var top = UI.sequence.top;
        var height = this.element.clientHeight;
        var y = dnd.y - this.offsetY;
        var f = 0.65;
        if (this.inbucket) {
            if (y > top - height * (1 - f)) {
                this.move_into_sequence(dnd);
            }
        }
        else {
            if (y < top - height * f) {
                this.move_into_bucket(dnd);
            }
        }
        if (this.inbucket) {
            this.on_mousemove_bucket(dnd);
        }
        else {
            this.on_mousemove_sequence(dnd);
        }
    },

    move_into_sequence: function(dnd) {
        if (!this.frombucket) {
            this.clear_over();
            UI.sequence.reset();
        }
        var seq = UI.sequence.element;
        if (seq.children.length == 0) {
            this.i = 0;
            this.orig_i = 0;
            this.target = this.element;
            seq.appendChild(this.element);
            this.update_offset();
            return;
        }
        
        var x = this.pos.left + dnd.dx;
        
        var scroll_x = x + seq.scrollLeft;
    
        var unclamped = Math.round(scroll_x / this.width);
        this.i = Math.max(0, Math.min(unclamped, seq.children.length));
        this.orig_i = this.i;
        if (this.i == seq.children.length) {
            this.over = seq.children[this.i - 1];
            this.over.classList.add('over-right');
        }
        else {
            this.over = seq.children[this.i];
            this.over.classList.add('over');
        }

        var ref = seq.children[this.i];
        $unparent(this.element);
        seq.insertBefore(this.element, ref);
        if (!ref) {
            seq.scrollLeft += this.width;
        }
        this.target = this.element;
        this.update_offset();
    },

    move_into_bucket: function(dnd) {
        this.stop_scrolling();
        $unparent(this.element);
        $('bucket').appendChild(this.element);
        if (this.frombucket) {
            this.clear_over();
            UI.sequence.reset();
        }
        this.update_offset();
    },

    update_offset: function() {
        this.offsetX = Math.round(this.dnd.offsetX * this.element.offsetWidth / this.offsetWidth);
        this.offsetY = Math.round(this.dnd.offsetY * this.element.offsetHeight / this.offsetHeight);
        console.log(this.offsetX + ',' + this.offsetY);
    },

    on_mousemove_bucket: function(dnd) {
        this.x = dnd.x - this.offsetX;
        this.y = dnd.y - this.offsetY;
    },

    start_scrolling: function(direction) {
        console.log(direction);
        this.direction = direction;
        this.scrolling = true;
        this.interval_id = setInterval($bind(this.on_interval, this), 300);
    },

    stop_scrolling: function() {
        console.log('stop');
        this.scrolling = false;
        clearInterval(this.interval_id);
        this.interval_id = null;
    },

    on_interval: function() {
        console.log('interval');
        var d = (this.direction == 'left') ? -1 : 1;
        UI.sequence.element.scrollLeft += (d * this.width);
        this.do_mousemove_sequence();
    },

    on_mousemove_sequence: function(dnd) {
        var mid_x = dnd.x - this.offsetX + (this.element.offsetWidth / 2);
        var width = UI.sequence.element.clientWidth;
        var left = Math.min(dnd.x, mid_x);
        var right = Math.max(dnd.x, mid_x);

        if (this.scrolling) {
            if (left > 0 && right < width) {
                this.stop_scrolling();
            }
            else {
                return;
            }
        }
        else {
            if (left <= 0) {
                this.start_scrolling('left');
            }
            else if (right >= width) {
                this.start_scrolling('right');
            }
        }
        this.do_mousemove_sequence();
    },
   
    do_mousemove_sequence: function() {
        var x = this.dnd.x - this.offsetX;
        var parent = UI.sequence.element;
        var scroll_x = x + parent.scrollLeft;
        var ix = this.i * this.width;
        var dx = scroll_x - ix;
        
        this.x = x; 
        this.y = UI.sequence.top - 14;

        if (dx < -this.threshold) {
            this.shift_right();
        }
        else if (dx > this.threshold) {
            this.shift_left();
        }
    },

    shift_right: function() {
        if (!this.target.previousSibling) {
            return;
        }
        this.i -= 1;
        if (this.target.classList.contains('left')) {
            this.target.classList.remove('left');
            UI.animate(this.target);
        }
        else {
            this.target.previousSibling.classList.add('right');
            UI.animate(this.target.previousSibling);
        }
        this.target = this.target.previousSibling;
    },

    shift_left: function() {
        if (!this.target.nextSibling) {
            return;
        }
        this.i += 1;
        if (this.target.classList.contains('right')) {
            this.target.classList.remove('right');
            UI.animate(this.target);
        }
        else {
            this.target.nextSibling.classList.add('left');
            UI.animate(this.target.nextSibling);
        }
        this.target = this.target.nextSibling;

    },

    clear_over: function() {
        if (this.over) {
            this.over.classList.remove('over');
            this.over.classList.remove('over-right');
            this.over = null;
        }
        UI.animate(null);
    },

    on_drop: function(dnd) {
        this.stop_scrolling();
        this.element.classList.remove('grabbed');
        this.clear_over();
        UI.sequence.reset();
        if (this.inbucket) {
            if (UI.bucket.lastChild != this.element) {
                $unparent(this.element);
                UI.bucket.appendChild(this.element);
            }
            var pos = $position(UI.bucket);
            this.x = dnd.x - this.offsetX - pos.left;
            this.y = dnd.y - this.offsetY - pos.top;
        }
        else {
            console.log(this.orig_i + ' => ' + this.i);
            this.x = null;
            this.y = null;
            var seq = $('sequence');
            if (this.i == this.orig_i) {
                console.assert(seq.children[this.i] == this.element);
            }
            else {
                if (this.i < this.orig_i) {
                    var ref = seq.children[this.i];
                }
                else {
                    var ref = seq.children[this.i].nextSibling;
                }
                $unparent(this.element);
                seq.insertBefore(this.element, ref);
            }
        }
        UI.sequence.do_reorder();
    },
}


function $compare(one, two) {
    if (! (one instanceof Array && two instanceof Array)) {
        return false;
    }
    if (one.length != two.length) {
        return false;
    }
    var i;
    for (i in one) {
        if (one[i] != two[i]) {
            return false;
        }
    }
    return true;
}


var Sequence = function(session, doc) {
    this.element = $('sequence');
    this.bucket = $('bucket');
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.on_change(doc);
    
    this.element.onmousedown = $bind(this.on_mousedown, this);
    this.element.onscroll = $bind(this.on_scroll, this);
}
Sequence.prototype = {
    get top() {
        return this.element.offsetTop + 29;
    },

    on_change: function(doc) {
        console.log('Sequence.on_change()');
        this.doc = doc;

        Thumbs.freeze();

        var i, _id, child, element;
        for (i in doc.node.src) {
            _id = doc.node.src[i];
            child = this.element.children[i];
            if (!child || child.id != _id) {
                element = UI.get_slice(_id);
                this.element.insertBefore(element, child);
            }
        }

        if (! doc.doodle instanceof Array) {
            UI.sequence.doc.doodle = [];
        }

        var obj;
        for (i in doc.doodle) {
            obj = doc.doodle[i];
            child = this.bucket.children[i];
            if (!child || child.id != obj.id) {
                element = UI.get_slice(obj.id);
                this.bucket.insertBefore(element, child);
                child = element;
            }
            child.style.left = obj.x + 'px';
            child.style.top = obj.y + 'px';
        }

        UI.select(doc.selected);

        Thumbs.unfreeze();

        console.assert(
            $compare(this.doc.node.src, this.get_src())
        );
    },

    on_scroll: function(event) {
        this.element.style.setProperty('background-position', -this.element.scrollLeft + 'px 0px');
    },

    on_mousedown: function(event) {
        console.log('sequence mousedown');
        this.dnd = new DragEvent(event, this.element);
        this.dnd.ondrag = $bind(this.on_drag, this);
        this.dnd.scrollLeft = this.element.scrollLeft;
    },

    on_drag: function(dnd) {  
        this.element.scrollLeft = dnd.scrollLeft - dnd.dx;  
    },

    get_src: function() {
        var i;
        var src = [];
        for (i=0; i<this.element.children.length; i++) {
            src.push(this.element.children[i].id);
        }
        return src;
    },

    get_doodle: function() {
        var i, child;
        var doodle = [];
        for (i=0; i<this.bucket.children.length; i++) {
            var child = this.bucket.children[i];
            doodle.push({
                id: child.id,
                x: parseInt(child.style.left),
                y: parseInt(child.style.top),
            });
        }
        return doodle;
    },

    do_reorder: function() {
        console.log('do_reorder');
        var src = this.get_src();
        var doodle = this.get_doodle();
        this.doc.node.src = src;
        this.doc.doodle = doodle;
        if (UI.selected) {
            this.doc.selected = UI.selected.id;
        }
        else {
            this.doc.selected = null;
        }
        this.session.save(this.doc, true);  // no_emit=true
        this.session.commit();
    },

    reset: function() {
        console.log('Sequence.reset()');
        var i, child;
        for (i=0; i<this.element.children.length; i++) {
            child = this.element.children[i];
            if (!child.classList.contains('grabbed')) {
                child.classList.remove('left');
                child.classList.remove('right');
            }
        }
    },
}


function frame_to_seconds(frame, framerate) {
    return frame * framerate.denom / framerate.num;
}


var VideoFrame = function(which) {
    this.video = $el('video', {'class': which});
    var callback = $bind(this.on_canplaythrough, this);
    this.video.addEventListener('canplaythrough', callback);
}
VideoFrame.prototype = {
    on_canplaythrough: function(event) {
        console.log('canplaythrough ' + this.index);
        this.ready = true;
        this.do_seek();
    },

    set_clip: function(clip) {
        this.ready = false;
        this.framerate = clip.framerate;
        this.frames = clip.duration.frames;
        this.pending = 0;
        this.current = null;
        this.video.src = 'dmedia:' + clip._id;
        this.video.load();
    },

    play: function() {
        this.video.play();
    },

    pause: function() {
        this.video.pause();
    },

    seek: function(index, now) {
        this.index = Math.max(0, Math.min(index, this.frames - 1));
        this.pending = frame_to_seconds(this.index, this.framerate);
        if (now) {
            this.current = null;
            this.do_seek();
        }
    },

    do_seek: function() {
        if (this.ready && this.pending != this.current) {
            this.current = this.pending;
            this.video.currentTime = this.pending;
        }
    },

    show: function() {
        this.video.classList.remove('hide');
    },

    hide: function() {
        this.video.pause();
        this.video.classList.add('hide');
    },

    get_x: function(width) {
        return Math.round(width * this.video.currentTime / this.video.duration);
    },

    get_frame: function() {
        return Math.round(this.frames * this.video.currentTime / this.video.duration);
    },
}


function create_node(node) {
    return {
        '_id': couch.random_id(),
        'ver': 0,
        'type': 'novacut/node',
        'time': couch.time(),
        'node': node,
    }
}


function create_slice(src, frame_count) {
    var node = {
        'type': 'slice',
        'src': src,
        'start': {'frame': 0},
        'stop': {'frame': frame_count},
        'stream': 'video',
    }
    return create_node(node);
}


var RoughCut = function(session) {
    this.session = session;
    this.active = false;

    this.element = $('roughcut');

    this.done = $el('button', {textContent: 'Done'});
    this.element.appendChild(this.done);
    this.done.onclick = function() {
        UI.hide_roughcut();
    }

    this.startvideo = new VideoFrame('start');
    this.endvideo = new VideoFrame('end hide');
    this.element.appendChild(this.startvideo.video);
    this.element.appendChild(this.endvideo.video);

    this.scrubber = $el('div', {'class': 'scrubber'});
    this.element.appendChild(this.scrubber);
    
    this.bar = $el('div', {'class': 'bar hide'});
    this.scrubber.appendChild(this.bar);

    this.playhead = $el('div', {'class': 'playhead hide'});
    this.scrubber.appendChild(this.playhead);

    this.scrubber.onmouseover = $bind(this.on_mouseover, this);
    this.scrubber.onmouseout = $bind(this.on_mouseout, this);
    this.scrubber.onmousedown = $bind(this.on_mousedown, this);
} 
RoughCut.prototype = {
    on_interval: function() {
        if (this.playing) {
            if (this.dnd) {
                this.startvideo.do_seek();
            }
            var frame = this.startvideo.get_frame();
            if (frame >= this.stop - 1) {
                console.log('stop');
                this.startvideo.seek(this.start, true);
                frame = this.start;
            }
            this.playhead.style.left = this.get_x(frame) + 'px';
        }
        this.startvideo.do_seek();
        this.endvideo.do_seek();
    },

    hide: function() {
        this.active = false;
        clearInterval(this.interval_id);
        this.mode = null;
        this.pause(); 
        $hide(this.element);
    },

    show: function(clip_id) {
        this.active = true;
        this.clip = this.session.get_doc(clip_id);
        this.frames = this.clip.duration.frames;
        this.reset();
        this.startvideo.set_clip(this.clip);
        this.endvideo.set_clip(this.clip);
        $show(this.element);
        this.interval_id = setInterval($bind(this.on_interval, this), 100);
    },

    reset: function() {
        delete this.dnd;
        this._start = 0;
        this._stop = this.frames;
        this.scrubber.onmousemove = null;
    },

    get_x: function(frame) {
        return Math.round(this.scrubber.clientWidth * frame / this.frames);
    },

    get_frame: function(x, key_unit) {
        var frame = Math.round(this.frames * x / this.scrubber.clientWidth);
        if (key_unit) {
            return 1 + Math.round(frame / 15) * 15;
        }
        return frame;
    },

    set start(value) {
        this._start = Math.max(0, Math.min(value, this._stop - 1));
        this.startvideo.seek(this._start);
    },

    get start() {
        return this._start;
    },

    set stop(value) {
        this._stop = Math.max(this._start + 1, Math.min(value, this.frames));
        this.endvideo.seek(this._stop - 1);
    },

    get stop() {
        return this._stop;
    },
 
    get left() {
        return this.get_x(this._start);
    },

    get right() {
        return this.get_x(this._stop);
    },

    playpause: function() {
        if (this.playing) {
            this.pause();
        }
        else {
            this.play();
        }
    },
 
    play: function() {
        this.playing = true;
        $show(this.playhead);
        this.scrubber.onmousemove = null;
        this.startvideo.play();
    },
 
    pause: function() {
        this.startvideo.pause();
        this.playing = false;
        $hide(this.playhead);
        if (this.mode == 'create') {
            this.bind_mousemove();
        }
    },
 
    update_bar: function() {
        var left = this.left;
        var width = Math.max(2, this.right - left);
        this.bar.style.left = left + 'px';
        this.bar.style.width = width + 'px';
    },

    sync_from_slice: function() {
        this._start = 0;
        this._stop = this.frames;
        this.start = this.slice.node.start.frame;
        this.stop = this.slice.node.stop.frame;
        this.update_bar();
    },

    save_to_slice: function() {
        /*
        Store start & stop in slice doc, mark doc as dirty.

        Note that this *only* marks the slice doc as dirty, does *not* call
        session.commit().  This is for cases when you also need to update the
        sequence doc, so you can send both in a single CouchDB request.
        */
        this.slice.node.start.frame = this.start;
        this.slice.node.stop.frame = this.stop;
        this.session.save(this.slice);
        console.log(JSON.stringify(this.slice));
    },

    create_slice: function() {
        console.log('create_slice');
        this.mode = 'create';
        this.endvideo.hide();
        this.reset();    
        this.bar.style.left = this.left + 'px';
        this.bar.style.width = '1px';
        this.slice = create_slice(this.clip._id, this.frames);
        this.bind_mousemove();
    },

    edit_slice: function(slice) {
        console.log('edit_slice ' + slice._id);
        this.mode = 'edit';
        this.slice = slice;
        this.endvideo.show();
        this.reset();
        $show(this.bar);
        this.sync_from_slice();
    },

    bind_mousemove: function() {
        this.scrubber.onmousemove = $bind(this.on_mousemove, this);
    },

    on_mouseover: function(event) {
        if (this.mode == 'create' && !this.playing && !this.dnd) {
            $show(this.bar);
        }
    },

    on_mouseout: function(event) {
        if (this.mode == 'create' && !this.playing && !this.dnd) {
            $hide(this.bar);
            this.start = 0;
        }
    },

    on_mousemove: function(event) {
        this.start = this.get_frame(event.clientX, true);
        this.bar.style.left = this.left + 'px';
    },

    on_mousedown: function(event) {
        this.scrubber.onmousemove = null;
        this.dnd = new DragEvent(event);
        this.dnd.ondragcancel = $bind(this.on_dragcancel, this);
        this.dnd.ondragstart = $bind(this.on_dragstart, this);

        if (this.playing) {
            this.startvideo.pause();
            var frame = Math.max(this.start, Math.min(this.get_frame(this.dnd.x), this.stop - 1));
            this.startvideo.seek(frame, true);
        }
        else if (this.mode == 'edit') {
            var mid = (this.left + this.right) / 2;
            this.point = (event.clientX <= mid) ? 'left' : 'right';
            var frame = this.get_frame(event.clientX, true);
            if (this.point == 'left') {
                this.start = frame;
            }
            else {
                this.stop = frame + 1;
            }
            this.update_bar();
        }
    },

    on_dragcancel: function(dnd) {
        delete this.dnd;
        if (this.playing) {
            this.startvideo.play();
            return;
        }
        if (this.mode == 'create') {
            this.bindmousemove();
        }
        else {
            this.sync_from_slice();
        }
    },
 
    on_dragstart: function(dnd) {
        this.dnd.ondrag = $bind(this.on_drag, this);
        this.dnd.ondrop = $bind(this.on_drop, this);
        if (!this.playing && this.mode == 'create') {
            this.endvideo.show();
            this.orig_start = this.start;
        }
    },

    on_drag: function(dnd) {
        var frame = this.get_frame(dnd.x, true);
        if (this.playing) {
            frame = Math.max(this.start, Math.min(frame, this.stop - 1));
            this.startvideo.seek(frame);
            return;
        }
        if (this.mode == 'create') {
            if (frame < this.orig_start) {
                this.start = frame;
                this.stop = this.orig_start + 1;
            }
            else {
                this.start = this.orig_start;
                this.stop = frame + 1;
            }
        }
        else {
            if (this.point == 'left') {
                this.start = frame;
            }
            else {
                this.stop = frame + 1;
            }
        }
        this.update_bar();
    },
 
    on_drop: function(dnd) {
        delete this.dnd;
        if (this.playing) {
            this.startvideo.play();
            return;
        }
        if (this.mode == 'create') {
            this.save_to_slice();
            UI.sequence.doc.doodle.push({id: this.slice._id, x: 16, y: 9});
            UI.sequence.doc.selected = this.slice._id;
            this.session.save(UI.sequence.doc);
            this.session.commit();
            this.edit_slice(this.slice);
        }
        else {
            this.save_to_slice();
            this.session.commit();
        }
    },



}


function Clips(coredb) {
    this.coredb = coredb;
    this.select = $('dmedia_project');
    this.select.onchange = $bind(this.on_change, this);
    this.div = $('clips');
    this.load_projects();
}
Clips.prototype = {
    load: function(id) {
        if (!id) {
            this.id = null;
            this.doc = null;
            this.db = null;
            return false;
        }
        this.id = id;
        this.doc = this.coredb.get_sync(id);
        this.db = new couch.Database(this.doc['db_name']);
        return true;
    },

    load_recent: function() {
        var rows = this.coredb.view_sync('project', 'atime',
               {limit: 1, descending: true}
        )['rows'];
        if (rows.length >= 1) {
            this.load(rows[0].id);
        }
        else {
            this.load(null);
        }
    },

    load_projects: function() {
        var callback = $bind(this.on_projects, this);
        this.coredb.view(callback, 'project', 'title');
    },

    on_projects: function(req) {
        var rows = req.read().rows;
        this.select.innerHTML = null;
        this.select.appendChild($el('option'));
        rows.forEach(function(row) {
            var option = $el('option', {textContent: row.key, value: row.id});
            this.select.appendChild(option);
        }, this);
    },

    on_change: function(event) {
        console.log(this.select.value);
        this.div.innerHTML = null;
        if (this.load(this.select.value)) {
            this.load_clips();
        }
    },

    load_clips: function() {
        var callback = $bind(this.on_clips, this);
        this.db.view(callback, 'user', 'video');
    },

    on_clips: function(req) {
        var rows = req.read().rows;
        this.div.innerHTML = null;
        var self = this;
        rows.forEach(function(row) {
            var id = row.id;
            var img = new Image();
            img.src = this.att_url(id);
            img.ondblclick = function(event) {
                UI.copy_clips([id]);
                UI.create_slice(id);
            }
            img.onmousedown = function(event) {
                self.on_mousedown(id, event);
            }
            this.div.appendChild(img);
        }, this);
    },

    on_mousedown: function(id, event) {
        this.target = id;
        this.dnd = new DragEvent(event);
        this.dnd.ondragcancel = $bind(this.on_dragcancel, this);
        this.dnd.ondragstart = $bind(this.on_dragstart, this);
    },

    on_dragcancel: function(dnd) {
        console.log('dragcancel' + this.target);
        delete this.dnd;
    },

    on_dragstart: function(dnd) {
        console.log('dragstart' + this.target);
        this.dnd.ondrag = $bind(this.on_drag, this);
        this.dnd.ondrop = $bind(this.on_drop, this);
    },

    on_drag: function(dnd) {
        console.log('dragcancel' + this.target);
    },

    on_drop: function(dnd) {
        console.log('drop');
        delete this.dnd;
    },

    att_url: function(doc_or_id, name) {
        if (!this.db) {
            return null;
        }
        return this.db.att_url(doc_or_id, name);
    },

    att_css_url: function(doc_or_id, name) {
        if (!this.db) {
            return null;
        }
        return this.db.att_css_url(doc_or_id, name);
    },
}


var UI = {
    animated: null,

    animate: function(element) {
        if (UI.animated) {
            UI.animated.classList.remove('animated');
        }
        UI.animated = $(element);
        if (UI.animated) {
            UI.animated.classList.add('animated');
        }
    },

    copy_clips: function(ids) {
        Hub.send('copy_docs', UI.clips.db.name, UI.db.name, ids);
    },

    selected: null,

    select: function(element) {
        $unselect(UI.selected);
        UI.selected = $select(element);
        if (UI.selected && UI.selected.parentNode.id == 'sequence') {
            var child = UI.selected;
            var seq = child.parentNode;
            if (child.offsetLeft < seq.scrollLeft) {
                console.log('scrolling left');
                seq.scrollLeft = child.offsetLeft;
            }
            else if (child.offsetLeft + child.offsetWidth > seq.scrollLeft + seq.clientWidth) {
                console.log('scrolling right');
                seq.scrollLeft = child.offsetLeft + child.offsetWidth - seq.clientWidth;
                
            }
        }
    },

    init: function() {
        window.addEventListener('keypress', UI.on_keypress);
        UI.bucket = $('bucket');
        UI.thumbnails = new couch.Database('thumbnails');
        var id = window.location.hash.slice(1);
        var doc = novacut.get_sync(id);
        UI.db = new couch.Database(doc.db_name);
        UI.doc = UI.db.get_sync(id);
        UI.project_id = id;
        UI.session = new couch.Session(UI.db, UI.on_new_doc);
        UI.session.start();
        UI.clips = new Clips(dmedia);
    },

    get_slice: function(_id) {
        var element = $unparent(_id);
        if (element) {
            console.log(_id);
            return element;
        }
        var slice = new Slice(UI.session, UI.session.get_doc(_id));
        return slice.element;
    },

    on_new_doc: function(doc) {
        if (doc._id == UI.doc.root_id) {
            UI.sequence = new Sequence(UI.session, doc);
        }
    },
    
    _roughcut: null,

    get roughcut() {
        if (UI._roughcut == null) {
            UI._roughcut = new RoughCut(UI.session);
        }
        return UI._roughcut;
    },
    
    create_slice: function(id) {
        UI.roughcut.show(id);
        UI.roughcut.create_slice();
    },

    edit_slice: function(doc) {
        UI.roughcut.show(doc.node.src);
        UI.roughcut.edit_slice(doc);
    },

    hide_roughcut: function() {
        UI.roughcut.hide();
    },

    on_keypress: function(event) {
        if (event.keyCode == 32) {
            $halt(event);
            if (UI.roughcut.active) {
                UI.roughcut.playpause();
            }
            else if (!UI.player) {
                UI.player = new sequence_viewer(UI.session, UI.sequence.doc);
                document.body.appendChild(UI.player.element);
                UI.player.play();
            }
        }
    },
}

window.addEventListener('load', UI.init);


