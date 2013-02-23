"use strict";

var db = new couch.Database('swhoosh');

function $halt(event) {
    event.preventDefault();
    event.stopPropagation();
}


var DragEvent = function(event, ondrag, ondrop) {
    $halt(event);
    this.event = event;
    this.x = event.clientX;
    this.y = event.clientY;
    this.ox = this.x;
    this.oy = this.y;
    this.dx = 0;
    this.dy = 0;

    this.ondrag = ondrag;
    this.ondrop = ondrop;

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
        this.x = event.clientX;
        this.y = event.clientY;
        this.dx = this.x - this.ox;
        this.dy = this.y - this.oy;
    },

    on_mousemove: function(event) {
        this.update(event);
        if (this.ondrag) {
            this.ondrag(this);
        }
    },

    on_mouseup: function(event) {
        this.update(event);
        if (this.ondrop) {
            this.update(event);
            this.ondrop(this);
        }
    },
}


var UI = {
    on_load: function() {
        try {
            UI.doc = db.get_sync('state');
        }
        catch (e) {
            UI.doc = {
                '_id': 'state',
                'playhead': 0,
            }
        }
        UI.scrubber = $('scrubber');
        UI.playhead = $('playhead');
        UI.scrubber.onmousedown = UI.on_mousedown;
        UI.set_value(UI.doc.playhead);
        UI.deactivate();
    },

    activate: function(value) {
        UI.active = true;
        UI.scrubber.classList.add('active');
        UI.set_value(value);
    },

    deactivate: function() {
        UI.active = false;
        UI.scrubber.classList.remove('active');
    },

    on_mousedown: function(event) {
        var dnd = new DragEvent(event, UI.on_drag, UI.on_drop);
        UI.start_value = UI.value;
        UI.activate(dnd.x);
    },

    on_drag: function(dnd) {
        if (UI.active) {
            if (dnd.y < UI.scrubber.offsetTop) {
                UI.deactivate();
                UI.set_value(UI.start_value);
            }
            else {
                UI.set_value(dnd.x);
            }
        }
        else {
            if (dnd.y >= UI.scrubber.offsetTop) {
                UI.activate(dnd.x);
            }
        }
    },

    on_drop: function(dnd) {
        if (UI.active) {
            UI.deactivate();
            UI.doc.playhead = UI.value;
            db.save(UI.doc);
        }
    },

    set_value: function(value) {
        UI.value = Math.max(0, Math.min(value, UI.scrubber.clientWidth - 1));
        UI.playhead.style.left = UI.value + 'px';
    },
}


window.addEventListener('load', UI.on_load);
