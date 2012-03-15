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

    this.on_change(doc);

    this.i = null;
    this.over = null;
    this.width = 192 + 2;
    this.threshold = this.width * 0.65;
    this.onreorder = null;
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
        if (doc.sink) {
            this.element.classList.remove('bucket');
            this.x = null;
            this.y = null;
            this.element.style.zIndex = null;
        }
        else {
            this.element.classList.add('bucket');
            this.x = doc.x;
            this.y = doc.y;
            this.element.style.zIndex = (doc.z_index || 0);
        }
    },

    on_mousedown: function(event) {
        $halt(event);
        this.parent = this.element.parentNode; 
        this.offsetX = event.offsetX;
        this.offsetY = event.offsetY;
        this.origY = event.pageY;
        this.element.classList.add('grabbed');
        var self = this;
        var tmp = {};
        tmp.on_mousemove = function(event) {
            self.on_mousemove(event);            
        }
        tmp.on_mouseup = function(event) {
            self.on_mouseup(event);
            window.removeEventListener('mousemove', tmp.on_mousemove);
            window.removeEventListener('mouseup', tmp.on_mouseup);
        }
        window.addEventListener('mousemove', tmp.on_mousemove);
        window.addEventListener('mouseup', tmp.on_mouseup);

        UI.top = null;
        if (this.frombucket) {
            UI.to_top(this.element);
            this.on_mousemove_bucket(event);
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
                }
            }
            this.on_mousemove_sequence(event);
        }
    },

    on_mousemove: function(event) {
        if (this.frombucket) {
            var dy = event.pageY - this.offsetY - UI.sequence.element.offsetTop;
        }
        else {
            var dy = event.pageY - this.origY;
        }
        var height = this.element.clientHeight;
        var threshold = height * 0.65;
        if (this.inbucket) {
            if (dy + height > threshold) {
                this.move_into_sequence(event);
            }
        }
        else {
            if (dy < -threshold) {
                this.move_into_bucket(event);
            }
        }
        if (this.inbucket) {
            this.on_mousemove_bucket(event);
        }
        else {
            this.on_mousemove_sequence(event);
        }
    },

    move_into_sequence: function(event) {
        this.element.classList.remove('bucket');
        if (!this.frombucket) {
            return;
        }
        var x = event.pageX - (this.offsetX * 1.5);
        var seq = UI.sequence.element;
        var scroll_x = x + seq.scrollLeft;
    
        var unclamped = Math.round(scroll_x / this.width);
        this.i = Math.max(0, Math.min(unclamped, seq.children.length));
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

    move_into_bucket: function(event) {
        console.log('move_into_bucket');
        this.element.classList.add('bucket');
        if (this.frombucket) {
            $unparent(this.element);
            this.parent.appendChild(this.element);
            UI.reset_sequence();
        }
        else {
            UI.to_top(this.element); 
        }
    },

    on_mousemove_bucket: function(event) {
        if (this.frombucket) {
            this.x = event.pageX - this.offsetX;
            this.y = event.pageY - this.offsetY;
        }
        else {
            this.x = event.pageX - (this.offsetX / 1.5);
            this.y = event.pageY - (this.offsetY / 1.5);
        }
    },

    on_mousemove_sequence: function(event) {
        if (this.frombucket) {
            var x = event.pageX - (this.offsetX * 1.5);
        }
        else {
            var x = event.pageX - this.offsetX;
        }
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
        }
        else {
            this.target.previousSibling.classList.add('right');
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
        }
        else {
            this.target.nextSibling.classList.add('left');
        }
        this.target = this.target.nextSibling;

    },

    on_mouseup: function(event) {
        if (this.over) {
            this.over.classList.remove('over');
            this.over.classList.remove('over-right');
            this.over = null;
        }
        this.element.classList.remove('grabbed');
        if (this.inbucket) {
            this.doc.x = this.x;
            this.doc.y = this.y;
            this.doc.z_index = UI.z_index;
            delete this.doc.sink;
            if (!this.frombucket) {
                console.log('physically moving to bucket ' + this.element.id);
                console.assert(this.element.parentNode.id == 'sequence');
                $unparent(this.element);
                $('bucket').appendChild(this.element);
            }
        }
        else {
            var seq = $('sequence');
            var ref = seq.children[this.i];
            if (ref != this.element) {
                console.log('reordering ' + this.element.id);
                $unparent(this.element);
                seq.insertBefore(this.element, ref);
            }
            this.doc.sink = UI.sequence.doc._id;
        }
        UI.reset_sequence();
        this.session.save(this.doc);
        if (this.onreorder) {
            this.onreorder();
        }
        this.session.commit();
    },
}


Array.prototype.compare = function(other) {
    if (this.length != other.length) {
        return false;
    }
    var i;
    for (i in this) {
        if (this[i] != other[i]) {
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
        this.element.innerHTML = null;
        var on_reorder = $bind(this.on_reorder, this);
        doc.node.src.forEach(function(_id) {
            var slice = new Slice(this.session, this.session.get_doc(_id));
            slice.onreorder = on_reorder;
            this.append(slice);
            if (slice.doc.sink != this.doc._id) {
                console.log('fixing ' + slice.doc._id);
                slice.doc.sink = this.doc._id;
                this.session.save(slice.doc);
            }
        }, this);
        this.session.commit();
    },

    get_src: function() {
        var i, child;
        var src = [];
        for (i=0; i<this.element.children.length; i++) {
            child = this.element.children[i];
            src.push(child.id);
        }
        return src;
    },

    append: function(child) {
        this.element.appendChild(child.element);
    },

    on_mousewheel: function(event) {
        $halt(event);
        var delta = wheel_delta(event) * (192 + 6);
        this.element.scrollLeft += delta;
    },

    on_reorder: function() {
        console.log('reorder');
        this.doc.node.src = this.get_src();
        this.session.save(this.doc);
    },
}


var UI = {
    z_index: 0,

    top: null,

    to_top: function(element) {
        if (element == UI.top) {
            console.log('same');
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

    on_new_doc: function(doc) {
        if (doc._id == UI.doc.root_id) {
            UI.sequence = new Sequence(UI.session, doc);
        }
        else if (doc.type == 'novacut/node' && doc.node.type == 'slice') {
            if (!doc.sink) {
                var slice = new Slice(UI.session, doc);
                UI.bucket.appendChild(slice.element);
                UI.z_index = Math.max(UI.z_index, doc.z_index || 0);
            }
        }
    },

    softly_reset_sequence: function() {
        var seq = $('sequence');
        var i, child;
        for (i=0; i<seq.children.length; i++) {
            child = seq.children[i];
            child.classList.remove('left');
            child.classList.remove('right');
        }
    },

    reset_sequence: function() {
        var seq = $('sequence');
        var i, child;
        for (i=0; i<seq.children.length; i++) {
            child = seq.children[i];
            child.setAttribute('class', 'slice');
            child.style.zIndex = null;
            child.style.left = null;
            child.style.top = null;
        }
    },
}

window.addEventListener('load', UI.init);


