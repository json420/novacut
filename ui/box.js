"use strict";

var Box = function(db, doc) {
    this.db = db;
    this.element = document.createElement("div");
    this.element.classList.add("thumb");
    this.clicked = false;
    this.sync(doc);

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
    sync: function(doc) {
        this.doc = doc;
        if (this.clicked) {
            return;
        }
        this.x = doc.x;
        this.y = doc.y;
        this.element.textContent = this._x + ', ' + this._y;
    },

    set x(value) {
        this._x = value;
        this.element.style.left = value + 'px';
    },

    set y(value) {
        this._y = value;
        this.element.style.top = value + 'px';
    },

    finish: function(e) {
        this.clicked = false;
        this.element.textContent = this._x + ', ' + this._y;
        if (this.doc.x == this._x && this.doc.y == this._y) {
            return;
        }
        this.doc.x = this._x;
        this.doc.y = this._y;
        this.db.dirty(this.doc);
        this.db.commit();
    },

    on_mousedown: function(e) {
        e.preventDefault();
        this.clicked  = true;
        this.offsetX = e.offsetX;
        this.offsetY = e.offsetY;
    },

    on_mouseup: function(e) {
        if (this.clicked === true) {
            this.finish();
        }
    },

    on_mouseout: function(e) {
        if (this.clicked === true) {
            this.finish();
        }
    },

    on_mousemove: function(e) {
        if (this.clicked === true) {
            this.x = e.clientX - this.offsetX;
            this.y = e.clientY - this.offsetY;
        }
    },  
}


var db = new couch.Database('box');
var boxes = {};

function init_box(_id) {
    try {
        var doc = db.get(_id);
    }
    catch (e) {
        var doc = {_id: _id, x: 20, y: 20};
        db.save(doc);
    }
    var box = new Box(db, doc);
    boxes[_id] = box;
    document.body.appendChild(box.element);
}


function on_changes(r) {
    r.results.forEach(function(row) {
        var doc = row.doc;
        if (boxes[doc._id]) {
            boxes[doc._id].sync(doc);
        }
    });
}


function boxit() {
    var r = db.get('_all_docs');
    r.rows.forEach(function(row) {
        init_box(row.id);
    });
    var since = db.get().update_seq;
    var m = db.monitor_changes(on_changes, since);
}

