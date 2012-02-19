"use strict";

function $unparent(id) {
    var child = $(id);
    if (child && child.parentNode) {
        child.parentNode.removeChild(child);
    }
    return child;
}


var Box = function(id) {
    this.id = id;
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
        this.element.classList.add('grabbed');
    },

    ungrab: function() {
        this.grabbed = false;
        this.x = null;
        this.element.classList.remove('grabbed');
        var children = Array.prototype.slice.call(this.element.parentNode.children);
        children.forEach(function(child) {
            child.classList.remove('right');
            child.classList.remove('left');
        });
    },

    on_mousedown: function(event) {
        event.preventDefault();
        this.orig_x = event.screenX;
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
            var rdx = dx - (130 * this.pos);
            if (rdx < -75) {
                this.shift_right();
            }
            else if (rdx > 75) {
                this.shift_left();
            }
        }
    },

    shift_right: function() {
        if (!this.target.previousSibling) {
            return;
        }
        this.pos -= 1;
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
        this.pos += 1;
        if (this.target.classList.contains('right')) {
            this.target.classList.remove('right');
        }
        else {
            this.target.nextSibling.classList.add('left');
        }
        this.target = this.target.nextSibling; 
    },
}

var boxes = {};

function boxit() {
    var sequence = $('sequence');
    ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'].forEach(function(id) {
        var box = new Box(id);
        boxes[id] = box;
        sequence.appendChild(box.element); 
    });    
}

