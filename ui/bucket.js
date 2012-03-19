"use strict";


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
    var pos = {x: element.offsetLeft, y: element.offsetTop};
    while (element.offsetParent) {
        element = element.offsetParent;
        pos.x += (element.offsetLeft - element.scrollLeft);
        pos.y += (element.offsetTop - element.scrollTop);
    }
    return pos;
}


var DragEvent = function(event) {
    $halt(event);
    this.x = event.clientX;
    this.y = event.clientY;
    this.ox = this.x;
    this.oy = this.y;
    this.dx = 0;
    this.dy = 0;
    this.offsetX = event.offsetX;
    this.offsetY = event.offsetY;
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
        var html = document.body.parentNode;
        this.x = Math.max(0, Math.min(event.clientX, html.clientWidth));
        this.y = Math.max(0, Math.min(event.clientY, html.clientHeight));
        this.dx = this.x - this.ox;
        this.dy = this.y - this.oy;
    },

    on_mousemove: function(event) {
        $halt(event);
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
        $halt(event);
        if (this.ondrop) {
            this.update(event);
            this.ondrop(this);
        }
    },
}


var Frame = function(file_id) {
    this.file_id = file_id;
    this.index = null;
    this.img = null;
    this.element = $el('div', {'class': 'frame'});
}
Frame.prototype = {
    set_index: function(index) {
        this.index = index;
        this.element.textContent = index + 1;
        var img = UI.thumbnails.att_css_url(this.file_id, index);
        if (img != this.img) {
            this.img = img;
            this.element.style.backgroundImage = img;
        }
    },
}



var Slice = function(session, doc) {
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.element = $el('div', {'class': 'slice', 'id': doc._id});

    var file_id = doc.node.src;

    this.start = new Frame(file_id);
    this.element.appendChild(this.start.element);

    this.end = new Frame(file_id);
    this.element.appendChild(this.end.element);

    this.element.onmousedown = $bind(this.on_mousedown, this);
    this.element.ondblclick = $bind(this.on_dblclick, this);

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
    },

    on_mousedown: function(event) {
        UI.select(this.element);
        this.pos = $position(this.element);
        this.dnd = new DragEvent(event);
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
            this.y = UI.sequence.element.offsetTop - 10;
        }
        this.element.classList.add('grabbed');
    },

    on_drag: function(dnd) {
        var top = UI.sequence.element.offsetTop;
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
        var x = this.pos.x + dnd.dx;
        var seq = UI.sequence.element;
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

    on_mousemove_sequence: function(dnd) {
        var x = dnd.x - this.offsetX;
        var parent = UI.sequence.element;
        var scroll_x = x + parent.scrollLeft;
        
        var ix = this.i * this.width;
        var dx = scroll_x - ix;
        
        this.x = x; 
        this.y = UI.sequence.element.offsetTop - 10;

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
        this.element.classList.remove('grabbed');
        this.clear_over();
        UI.sequence.reset();
        if (this.inbucket) {
            if (UI.bucket.lastChild != this.element) {
                $unparent(this.element);
                UI.bucket.appendChild(this.element);
            }
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
}
Sequence.prototype = {
    on_change: function(doc) {
        console.log('Sequence.on_change()');
        this.doc = doc;

        var i, _id, child, element;
        for (i in doc.node.src) {
            _id = doc.node.src[i];
            child = this.element.children[i];
            if (!child || child.id != _id) {
                element = UI.get_slice(_id);
                this.element.insertBefore(element, child);
            }
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
    
        console.assert(
            $compare(this.doc.node.src, this.get_src())
        );
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
        this.session.save(this.doc);
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


var VideoFrame = function(clip, which) {
    this.framerate = clip.framerate;
    this.count = clip.duration.frames;
    this.video = $el('video', {'class': which});
    this.video.src = 'dmedia:' + clip._id;
    this.video.load();
    this.pending = 0;
    this.current = 0;
}
VideoFrame.prototype = {
    seek: function(index) {
        this.index = Math.max(0, Math.min(index, this.count - 1));
        this.pending = frame_to_seconds(this.index, this.framerate);
    },

    do_seek: function() {
        if (this.pending != this.current) {
            this.current = this.pending;
            this.video.currentTime = this.pending;
        }
    },

    show: function() {
        this.video.classList.remove('hide');
    },

    hide: function() {
        this.video.classList.add('hide');
    },
}


var RoughCut = function(session, clip_id) {
    this.session = session;
    this.clip = session.get_doc(clip_id);
    this.frames = this.clip.duration.frames;

    this.element = $('roughcut');

    this.done = $el('button', {textContent: 'Done'});
    this.element.appendChild(this.done);

    this.startvideo = new VideoFrame(this.clip, 'start');
    this.endvideo = new VideoFrame(this.clip, 'end hide');
    this.element.appendChild(this.startvideo.video);
    this.element.appendChild(this.endvideo.video);

    this.scrubber = $el('div', {'class': 'scrubber'});
    this.element.appendChild(this.scrubber);
    this.bar = $el('div', {'class': 'bar'});
    this.scrubber.appendChild(this.bar);
    $show(this.element);
    this.interval_id = setInterval($bind(this.on_interval, this), 150);
}
RoughCut.prototype = {
    on_interval: function() {
        this.startvideo.do_seek();
        this.endvideo.do_seek();
    },

    reset: function() {
        this._start = 0;
        this._stop = this.frames;
        this.dnd = null;
        this.scrubber.onmousedown = null;
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

    create_slice: function() {
        console.log('create_slice');
        this.endvideo.hide();
        this.reset();    
        this.bar.style.left = this.left + 'px';
        this.bar.style.width = '1px';
        this.scrubber.onmousemove = $bind(this.on_mousemove1, this);
        this.scrubber.onmousedown = $bind(this.on_mousedown1, this);
    },

    on_mousemove1: function(event) {
        this.start = this.get_frame(event.clientX, true);
        this.bar.style.left = this.left + 'px';
    },

    on_mousedown1: function(event) {
        console.log('mousedown1');
        this.scrubber.onmousemove = null;
        this.dnd = new DragEvent(event);
        this.dnd.ondragcancel = $bind(this.on_dragcancel1, this);
        this.dnd.ondragstart = $bind(this.on_dragstart1, this);
    },

    on_dragcancel1: function(dnd) {
        console.log('dragcancel1');
        this.dnd = null;
        this.scrubber.onmousemove = $bind(this.on_mousemove1, this);
    },  

    on_dragstart1: function(dnd) {
        console.log('dragstart1');
        this.dnd.ondrag = $bind(this.on_drag1, this);
        this.dnd.ondrop = $bind(this.on_drop1, this);
        this.endvideo.show();
        this.orig_start = this.start;
    },

    on_drag1: function(dnd) {
        var frame = this.get_frame(dnd.x, true);
        if (frame < this.orig_start) {
            this.start = frame;
            this.stop = this.orig_start + 1;
        }
        else {
            this.start = this.orig_start;
            this.stop = frame + 1;
        }
        this.update_bar();
    },

    on_drop1: function(dnd) {
        console.log('drop1');
        this.dnd = null;
    },

    edit_slice: function(slice) {
        console.log('edit_slice ' + slice._id);
        this.slice = slice;
        this.endvideo.show();
        this.reset();
        this.sync_from_slice();
        this.scrubber.onmousedown = $bind(this.on_mousedown2, this);
    },

    on_mousedown2: function(event) {
        console.log('mousedown2');
        var mid = (this.left + this.right) / 2;
        this.point = (event.clientX <= mid) ? 'left' : 'right';
        console.log(this.point);
        var frame = this.get_frame(event.clientX, true);
        if (this.point == 'left') {
            this.start = frame;
        }
        else {
            this.stop = frame + 1;
        }
        this.update_bar();
        this.dnd = new DragEvent(event);
        this.dnd.ondragcancel = $bind(this.on_dragcancel2, this);
        this.dnd.ondragstart = $bind(this.on_dragstart2, this);
    },

    on_dragcancel2: function(dnd) {
        console.log('dragcancel2');
        this.dnd = null;
        this.sync_from_slice();
    },  

    on_dragstart2: function(dnd) {
        console.log('dragstart');
        this.dnd.ondrag = $bind(this.on_drag2, this);
        this.dnd.ondrop = $bind(this.on_drop2, this);
    },

    on_drag2: function(dnd) {
        var frame = this.get_frame(dnd.x, true);
        if (this.point == 'left') {
            this.start = frame;
        }
        else {
            this.stop = frame + 1;
        }
        this.update_bar();
    },

    on_drop2: function(dnd) {
        console.log('drop2');
        this.dnd = null;
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

    selected: null,

    select: function(element) {
        $unselect(UI.selected);
        UI.selected = $select(element);
        if (UI.selected && UI.selected.parentNode.id == 'sequence') {
            var child = UI.selected;
            var seq = $('sequence');
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
        UI.bucket = $('bucket');
        UI.thumbnails = new couch.Database('thumbnails');
        var id = window.location.hash.slice(1);
        var doc = novacut.get_sync(id);
        UI.db = new couch.Database(doc.db_name);
        UI.doc = UI.db.get_sync(id);
        UI.project_id = id;
        UI.session = new couch.Session(UI.db, UI.on_new_doc);
        UI.session.start();
    },

    get_slice: function(_id) {
        var element = $unparent(_id);
        if (element) {
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

    edit_slice: function(doc) {
        UI.roughcut = new RoughCut(UI.session, doc.node.src);
        UI.roughcut.create_slice();
        //UI.roughcut.edit_slice(doc);
        //var url = ['slice.html#', UI.project_id, '/', doc._id].join('');
        //window.location.assign(url);
    },
}

window.addEventListener('load', UI.init);


