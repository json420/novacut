"use strict";


function thumbnail(_id, i) {
    return ['/novacut', _id, i + '.jpg'].join('/');
}

function wheel_delta(event) {
    var delta = event.wheelDeltaY;
    var scale = (event.shiftKey) ? -10 : -1;
    return scale * (delta / Math.abs(delta));
}

var Slice = function(db, doc) {
    this.db = db;
    this.element = $el('div', {'class': 'slice'});
    this.start = $el('img');
    this.end = $el('img');
    this.element.appendChild(this.start);
    this.element.appendChild(this.end);
    this.sync(doc);
    var self = this;
    this.start.onmousewheel = function(event) {
        self.on_mousewheel_start(event);
    }
    this.end.onmousewheel = function(event) {
        self.on_mousewheel_end(event);
    }
}
Slice.prototype = {
    on_mousewheel_start: function(event) {
        event.preventDefault();
        var delta = wheel_delta(event);
        var start = this.doc.node.start.frame;
        var stop = this.doc.node.stop.frame;
        var proposed = Math.max(0, Math.min(start + delta, stop - 1));
        if (start != proposed) {
            this.doc.node.start.frame = proposed;
            this.save();
        }   
    },

    on_mousewheel_end: function(event) {
        event.preventDefault();
        var delta = wheel_delta(event);
        var start = this.doc.node.start.frame;
        var stop = this.doc.node.stop.frame;
        var proposed = Math.max(start + 1, Math.min(stop + delta, this.count));
        if (stop != proposed) {
            this.doc.node.stop.frame = proposed;
            this.save();
        }   
    },

    append_to: function(parent) {
        parent.appendChild(this.element);
    },
    
    save: function() {
        this._sync(this.doc.node);
    },

    sync: function(doc) {
        this.doc = doc;
        var node = doc.node;
        this.count = docs[node.src].duration.frames;
        this._sync(node);
    },

    _sync: function(node) {
        this.start.setAttribute('src', thumbnail(node.src, node.start.frame));
        this.end.setAttribute('src', thumbnail(node.src, node.stop.frame - 1));
    },
    
    
}

