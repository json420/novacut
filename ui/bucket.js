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


var DragEvent = function(event, ondrag, ondrop) {
    $halt(event);
    this.ondrag = ondrag;
    this.ondrop = ondrop;
    this.x = event.clientX;
    this.y = event.clientY;
    this.ox = this.x;
    this.oy = this.y;
    this.dx = 0;
    this.dy = 0;

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
        if (this.ondrag) {
            this.update(event);
            this.ondrag(this);
        }
    },

    on_mouseup: function(event) {
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



var Slice = function(session, doc, forbucket) {
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.element = $el('div', {'class': 'slice', 'id': doc._id});

    var forbucket = forbucket || false;
    if (forbucket) {
        this.element.classList.add('bucket');
    }

    var file_id = doc.node.src;

    this.start = new Frame(file_id);
    this.element.appendChild(this.start.element);

    this.end = new Frame(file_id);
    this.element.appendChild(this.end.element);

    this.element.onmousedown = $bind(this.on_mousedown, this);

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
        return this.element.classList.contains('bucket');
    },

    get frombucket() {
        return this.parent && this.parent.id == 'bucket';
    },

    on_change: function(doc) {
        this.doc = doc;
        var node = doc.node;
        this.start.set_index(node.start.frame);
        this.end.set_index(node.stop.frame - 1);
        if (this.inbucket) {
            this.x = doc.x;
            this.y = doc.y;
            //this.element.style.zIndex = (doc.z_index || 0);
        }
        else {
            this.x = null;
            this.y = null;
            this.element.style.zIndex = null;
        }
    },

    on_mousedown: function(event) {
        this.pos = $position(this.element);
        this.dnd = new DragEvent(event, $bind(this.on_drag, this), $bind(this.on_drop, this));
        this.parent = this.element.parentNode;
        if (this.frombucket) {
            UI.to_top(this.element);
            this.on_mousemove_bucket(this.dnd);
        }
        else {
            if (this.element.nextSibling) {
                this.over = this.element.nextSibling;
                this.over.classList.add('over'); 
            }
            if (this.element.nextSibling) {
                this.over = this.element.nextSibling;
                this.over.classList.add('over'); 
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
            this.on_mousemove_sequence(this.dnd);
        }
        this.element.classList.add('grabbed');
    },

    on_drag: function(dnd) {
        var top = UI.sequence.element.offsetTop;
        var height = this.element.clientHeight;
        var y = this.pos.y + dnd.dy;
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
        this.element.classList.remove('bucket');
        if (!this.frombucket) {
            return;
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
    },

    move_into_bucket: function(dnd) {
        this.element.classList.add('bucket');
        if (this.frombucket) {
            $unparent(this.element);
            this.parent.appendChild(this.element);
            UI.sequence.reset();
        }
        else {
            UI.to_top(this.element);
        }
    },

    on_mousemove_bucket: function(dnd) {
        this.x = this.pos.x + dnd.dx;
        this.y = this.pos.y + dnd.dy;
    },

    on_mousemove_sequence: function(dnd) {
        var x = this.pos.x + dnd.dx;
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
            UI.set_animated(this.target);
        }
        else {
            this.target.previousSibling.classList.add('right');
            UI.set_animated(this.target.previousSibling);
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
            UI.set_animated(this.target);
        }
        else {
            this.target.nextSibling.classList.add('left');
            UI.set_animated(this.target.nextSibling);
        }
        this.target = this.target.nextSibling;

    },

    on_drop: function(dnd) {
        this.element.classList.remove('grabbed');
        if (this.over) {
            this.over.classList.remove('over');
            this.over.classList.remove('over-right');
            this.over = null;
        }
        if (this.inbucket) {
            if (!this.frombucket) {
                console.assert(this.element.parentNode.id == 'sequence');
                $unparent(this.element);
                $('bucket').appendChild(this.element);
            }
        }
        else {
            console.log(this.orig_i + ' => ' + this.i);
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
        if (UI.on_reorder) {
            UI.on_reorder();
        }
        this.session.commit();
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
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.on_change(doc);
}
Sequence.prototype = {
    on_change: function(doc) {
        this.doc = doc;
        if ($compare(doc.node.src, this.get_src())) {
            this.reset();
            return;
        }
        var i, _id, child, element;
        for (i in doc.node.src) {
            _id = doc.node.src[i];
            child = this.element.children[i];
            if (!child || child.id != _id) {
                element = UI.get_slice(_id);
                this.element.insertBefore(element, child);
            }
        }
        if (doc.node.src.length != this.element.children.length) {
            var remove = [];
            for (i=doc.node.src.length; i<this.element.children.length; i++) {
                remove.push(this.element.children[i]);
            }
            remove.forEach(function(boot) {
                UI.move_to_bucket(boot);   
            });
        }
        this.reset();
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

    on_mousewheel: function(event) {
        $halt(event);
        var delta = wheel_delta(event) * (192 + 6);
        this.element.scrollLeft += delta;
    },

    on_reorder: function() {
        console.log('reorder');
        var src = this.get_src();
        if ($compare(this.doc.node.src, src)) {
            console.log('already in correct order');
            this.reset();
            return;
        }
        this.doc.node.src = src;
        this.session.save(this.doc);
    },

    reset: function() {
        console.log('Sequence.reset()');
        var i, child;
        for (i=0; i<this.element.children.length; i++) {
            child = this.element.children[i];
            child.setAttribute('class', 'slice');
            child.style.zIndex = null;
            child.style.left = null;
            child.style.top = null;
        }
    },
}


var UI = {
    animated: null,
    
    set_animated: function(element) {
        if (UI.animated) {
            UI.animated.classList.remove('animated');
        }
        UI.animated = element;
        UI.animated.classList.add('animated');
    },

    z_index: 0,

    top: null,
    
    _sequence: null,

    get sequence() {
        if (!UI._sequence) {
            UI._sequence = new Sequence(UI.session, UI.session.get_doc(UI.doc.root_id));
            UI.on_reorder = $bind(UI._sequence.on_reorder, UI._sequence);
        }
        return UI._sequence;
    },

    to_top: function(element) {
        if (element == UI.top) {
            return;
        }
        UI.top = element;
        UI.z_index += 1;
        element.style.zIndex = UI.z_index;
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
    
    move_to_bucket: function(child) {
        child = $unparent(child);
        child.classList.add('bucket');
        UI.bucket.appendChild(child);
        return child;
    },

    on_new_doc: function(doc) {
        if (doc.type == 'novacut/node' && doc.node.type == 'slice') {
            if (UI.sequence.doc.node.src.indexOf(doc._id) >= 0) {
                // We don't create slices that the sequence will create itself
                return;
            }
            var slice = new Slice(UI.session, doc, true);
            UI.bucket.appendChild(slice.element);
            UI.z_index = Math.max(UI.z_index, doc.z_index || 0);
        }
    },

    set_marker: function(x, y) {
        var marker = $show('marker');
        marker.style.left = x + 'px';
        marker.style.top = y + 'px';
        marker.textContent = x + ',' + y;
    },
}

window.addEventListener('load', UI.init);


