"use strict";

var Box = function(id) {
    this.element = $el('div', {'class': 'slice', 'id': id, 'textContent': id});
    this.grabbed = false;
    var self = this;
    this.element.onmousedown = function(e) {
        return self.on_mousedown(e);
    }
    this.element.onmouseup = function(e) {
        return self.on_mouseup(e);
    }   
    this.element.onmouseout = function(e) {
        return self.on_mouseout(e);
    }
    this.element.onmousemove = function(e) {
        return self.on_mousemove(e);
    }
}
Box.prototype = {
    set x(value) {
        this.element.style.left = value + 'px';
    },

    set y(value) {
        this.element.style.top = value + 'px';
    },

    grab: function() {
        this.grabbed = true;
        this.element.classList.add('grabbed');
    },

    ungrab: function() {
        this.grabbed = false;
        this.element.classList.remove('grabbed');
    },

    on_mousedown: function(event) {
        event.preventDefault();
        this.orig_x = event.screenX;
        this.orig_y = event.screenY;
        this.x = 0;
        this.y = 0;
        this.grab();
    },

    on_mouseup: function(e) {
        if (this.grabbed === true) {
            this.ungrab();
        }
    },

    on_mouseout: function(e) {
        if (this.grabbed === true) {
            this.ungrab();
        }
    },

    on_mousemove: function(event) {
        if (this.grabbed === true) {
            event.preventDefault();
            var dx = event.screenX - this.orig_x;
            this.x = dx;
        }
    },  
}

var boxes = {};

function boxit() {
    var sequence = $('sequence');
    ['A', 'B', 'C'].forEach(function(id) {
        var box = new Box(id);
        boxes[id] = box;
        sequence.appendChild(box.element); 
    });    
}

