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

    var src = session.get_doc(doc.node.src);
    
    if (src.duration){
        this.count = src.duration.frames
    }
    else{
        this.count = src.meta.duration.frames;
    }

    var src = doc.node.src;
    this.start = new Frame(src);
    this.element.appendChild(this.start.element);

    this.indicator = new SliceIndicator();
    this.element.appendChild(this.indicator.element);

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

    this.element.onmousedown = function(e) {
        return self.on_mousedown(e);
    }
    this.size = 192 + 6;
    this.threshold = this.size * 0.6;
    
    this.onreorder = null;
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
        this.indicator.update(node.start.frame, node.stop.frame, this.count);
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

    get x() {
        return parseInt(this.element.style.left);
    },
    
    get y() {
        return parseInt(this.element.style.top);
    },

    grab: function() {
        this.target = this.element;
        this.pos = 0;
        this.x = 0;
        var children = Array.prototype.slice.call(this.element.parentNode.children);
        children.forEach(function(child) {
            child.classList.remove('home');
        });
        this.element.classList.add('grabbed');
    },

    ungrab: function(event) {
        this.x = null;
        this.y = null;
        this.element.classList.remove('grabbed');
        if (this.element.classList.contains("free") == true){
            this.bucket = true;
            
        }
        this.element.classList.remove('free');
        var i, me, child;
        var parent = this.element.parentNode;
        for (i=0; i<parent.children.length; i++) {
            child = parent.children[i];
            if (child == this.element) {
                me = i;
            }
            child.setAttribute('class', 'slice');
        }
        if (this.pos !== 0) {
            var target = parent.children[me + this.pos];
            parent.removeChild(this.element);
            if (this.bucket && UI.bucket){
                UI.bucket.add(event, this.doc._id);
            }
            else if (this.pos < 0) {
                parent.insertBefore(this.element, target);
            }
            else {
                parent.insertBefore(this.element, target.nextSibling);
            }
            if (this.onreorder) {
                this.onreorder();
            }
        }
        else {
            this.element.classList.add('home');  
        }
    },

    on_mousedown: function(event) {
        $halt(event);
        var self = this;
        var tmp = {};
        tmp.on_mousemove = function(event) {
            self.on_mousemove(event);
        }
        tmp.on_mouseup = function(event) {
            self.ungrab(event);
            window.removeEventListener('mousemove', tmp.on_mousemove);
            window.removeEventListener('mouseup', tmp.on_mouseup);
        }
        window.addEventListener('mousemove', tmp.on_mousemove);
        window.addEventListener('mouseup', tmp.on_mouseup);
        this.offsetX = event.offsetX;
        this.offsetY = event.offsetY;
        this.origX = event.screenX;
        this.origY = event.screenY;
        this.grab();
    },

    on_mousemove: function(event) {
        $halt(event);
        //return this.do_grabbed(event);
        if (this.element.classList.contains('grabbed')) {
            this.do_grabbed(event);
        }
        else if (this.element.classList.contains('free')) {
            this.do_free(event);
        }
    },

    do_grabbed: function(event) {
        var dy = event.screenY - this.origY;
        if (dy < -108) {
            this.element.classList.remove('grabbed');
            this.element.classList.add('free');
            if (this.element.previousSibling) {
                this.element.previousSibling.classList.add('marginright');
            }
            else if (this.element.nextSibling) {
                this.element.nextSibling.classList.add('marginleft');
            }
            return this.do_free(event);
        }
        var dx = event.screenX - this.origX;
        this.x = dx;
        var rdx = dx - (this.size * this.pos);
        if (rdx < -this.threshold) {
            this.shift_right();
        }
        else if (rdx > this.threshold) {
            this.shift_left();
        }
    },

    do_free: function(event) {
        this.x = event.clientX - this.offsetX;
        this.y = event.clientY - this.offsetY;
        this.pos = false;
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
    this.element = $('sequence');  //$el('div', {'class': 'sequence', 'id': doc._id});
    //this.items = new Items(this.element);
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.on_change(doc);
    this.element.ondragenter = $bind(this.on_dragenter, this);
    this.element.ondragover = $bind(this.on_dragover, this);
    this.element.ondrop = $bind(this.on_drop, this);
}
Sequence.prototype = {
    on_change: function(doc) {
        console.log('onchange');
        this.doc = doc;
        if (this.doc.node.src.compare(this.get_src())) {
            console.log('  no change');
            return;
        }
        this.element.innerHTML = null;
        var on_reorder = $bind(this.on_reorder, this);
        doc.node.src.forEach(function(_id) {
            var slice = new Slice(this.session, this.session.get_doc(_id));
            slice.onreorder = on_reorder;
            this.append(slice);
        }, this);
        Thumbs.flush();
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
        this.session.commit();
    },
}

var Bucket = function(session, doc){
    this.element = $('bucket');
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.on_change(doc);
    
    this.element.addEventListener("mousedown", $bind(this.on_mousedown, this));
}
Bucket.prototype = {
    on_change: function(doc){
        var self = this;
        self.doc = doc;
        var start = Date.now();
        self.element.innerHTML = "";
        self.doc.nodes.forEach(function(node){
            var node_doc = self.session.get_doc(node.id);
            if (node_doc.type == "dmedia/file"){
                //add a clip
            }
            else if (node_doc.type == "novacut/node"){
                switch(node_doc.node.type){
                    case "slice":
                        var node_obj = new Slice(self.session, node_doc);
                        node_obj.element.classList.add("bucket");
                        node_obj.x = node.pos.x
                        node_obj.y = node.pos.y
                        self.element.appendChild(node_obj.element);
                }
            };
        });
        Thumbs.flush();
        console.log(Date.now() - start);
    },
    
    add: function(event, id){
        var node = {};
        node.id = id;
        node.pos = {};
        console.log(event);
        node.pos.x = event.clientX;
        node.pos.y = event.clientY;
        if (this.doc.nodes.map(function(n){return n.id}).indexOf(id) == -1){
            this.doc.nodes.push(node);
            this.session.save(this.doc);
            this.session.commit();
        };
    },
    
    on_mousedown: function(event){
        $halt(event);
        this.startX = event.clientX;
        this.startY = event.clientY;
        document.body.style.cursor = "move";
        var tmp = {};
        tmp.on_mousemove = $bind(function(event){
            this.on_mousemove(event)
        }, this);
        tmp.on_mouseup = function(event){
            window.removeEventListener("mousemove", tmp.on_mousemove);
            window.removeEventListener("mouseup", tmp.on_mousemove);
            document.body.style.cursor = "auto";
        };
        window.addEventListener("mousemove", tmp.on_mousemove);
        window.addEventListener("mouseup", tmp.on_mouseup);
    },
    
    on_mousemove: function(event){
        var offsetX = event.clientX - this.startX;
        var offsetY = event.clientY - this.startY;
        this.element.scrollLeft -= offsetX;
        this.element.scrollTop -= offsetY;
        this.startX = event.clientX;
        this.startY = event.clientY
    },
}

var Clip = function(session, doc) {
    var self = this;
    session.subscribe(doc._id, this.on_change, this);
    this.session = session;
    this.element = $el('div', {'class': 'clip', 'id': doc._id});

    this.posX = 0;
    this.posY = 0;
    
    self.moveTo = function(x,y){
        self.stepTo(x, y);
        if (self.posX != x || self.posY != y){
            setTimeout(function(){
                self.moveTo(x, y);
            }, 30);
        }
    }

    if (doc.duration){
        this.count = doc.duration.frames;
    }
    else{
        this.count = doc.meta.duration.frames;
    }
    
    this.time = doc.ctime;
    
    this.frame_widget = new Frame(doc._id);
    this.element.appendChild(this.frame_widget.element);

    this.on_change(doc, true);
    
    this.element.ondblclick = $bind(this.on_dblclick, this);
    this.element.onmousedown = $bind(this.on_mousedown, this);
    this.element.onmousemove = $bind(this.on_mousemove, this);
    this.frame_widget.element.onmousewheel = $bind(this.on_mousewheel, this);
}
Clip.prototype = {
    on_change: function(doc) {
        this.doc = doc;
        this.frame_widget.set_index(0);
    },
    
    get posX(){
        return parseInt(this.element.style.getPropertyValue("left"));
    },
    
    set posX(value){
        this.element.style.setProperty("left", value + "px");
    },
    
    get posY(){
        return parseInt(this.element.style.getPropertyValue("top"));
    },
    
    set posY(value){
        this.element.style.setProperty("top", value + "px");
    },
    
    stepTo: function(x,y){
        var dx = (x - this.posX)/2;
        var dy = (y - this.posY)/2;
        
        if (dx > 0){
            this.posX += Math.ceil(dx);
        }
        else{
            this.posX += Math.floor(dx);
        }
        
        
        if (dy > 0){
            this.posY += Math.ceil(dy);
        }
        else{
            this.posY += Math.floor(dy);
        }
    },
    
    on_mousedown: function(event){
        $halt(event);
        if (event.button === 1){
            return false;
        }
        var self = this;
        var id = this.element.id;
        var el = this.element;
        var offsetX = event.offsetX;
        var offsetY = event.offsetY;
        var startX = event.clientX;
        var startY = event.clientY;
        var free = false;
        var parentElement = el.parentElement;
        var tmp_move = function(event){
            self.posX = (event.clientX - offsetX);
            if (!free){
                self.posY = (event.clientY - offsetY - parentElement.offsetTop + parentElement.scrollTop);
            }
            else{
                self.posY = (event.clientY - offsetY);
                if (UI.mouse_over_id !== event.target.id){
                    UI.mouse_over_id = event.target.id;
                    console.log("Drag over: " + UI.mouse_over_id);
                }
            }
            document.body.style.setProperty("cursor", "move")
        };
        var tmp_up = function(event){
            clearTimeout(t);
            window.removeEventListener("mousemove", tmp_move);
            window.removeEventListener("mouseup", tmp_up);
            document.body.style.setProperty("cursor", "auto")
            el.classList.remove("moving");
            
            if (el.parentElement !== parentElement){
                el.parentElement.removeChild(el);
                parentElement.appendChild(el);
            }
            if (UI.mouse_over_id && UI.mouse_over_id == "sequence" || UI.mouse_over_id == "slice"){
                console.log(UI.mouse_over_id);
                self.on_dblclick(event);
                UI.views.clips.flow();
            }
            if (free){
                self.posY += parentElement.scrollTop - parentElement.offsetTop;
            }
            UI.views.clips.flow(UI.views.clips.by_time);
        };
        var timeout = function(){
            el.classList.add("moving");
            free = true;
            el.parentElement.removeChild(el);
            self.posY += parentElement.offsetTop - parentElement.scrollTop;
            document.body.appendChild(el);
        };
        
        var t = setTimeout(timeout, 150);
        window.addEventListener("mouseup", tmp_up);
        window.addEventListener("mousemove", tmp_move);
    },
    
    on_dblclick: function(event){
        $halt(event);
        var id = this.element.id;
        var slice = {
            "_id": couch.random_id(), 
            "node": {
                "src": id, 
                "start": {
                    "frame": 0
                }, 
                "stop": {
                    "frame": this.count-1
                }, 
                "stream": "video", 
                "type": "slice"
            }, 
            "type": "novacut/node"
        };
        UI.session.save(slice);
        UI.sequence.doc.node.src.push(slice._id);
        UI.session.save(UI.sequence.doc);
        UI.session.commit();
    },
    
    on_mousewheel: function(event) {
        if(event.altKey){
            $halt(event);
            thingy = this;
        }
        else{
            return;
        }
        var delta = wheel_delta(event);
        var start = this.frame;
        var stop = this.doc.duration.frames;
        var proposed = Math.max(0, Math.min(start + delta, stop - 1));
        if (start != proposed) {
            this.frame = proposed;
        }
    },
    
    on_mousemove: function(event){
        if(event.button != 1){
            return;
        }
        var frames = this.doc.duration.frames - 1;
        var pos = event.offsetX/event.target.clientWidth;
        var frame = Math.floor(pos*frames);
        this.frame = frame;
    },
    
    set frame(val){
        this.frame_widget.set_index(val);
        Thumbs.flush();
    },
    
    get frame(){
        return this.frame_widget.index;
    },
}

var thingy;

var UI = {
    init: function() {
        UI.player = $('player');
        Hub.connect('render_finished', UI.on_render_finished);
        Hub.connect('state_hashed', UI.on_state_hashed);
        Hub.connect('job_hashed', UI.on_job_hashed);

        var id = window.location.hash.slice(1);
        var doc = novacut.get_sync(id);
        UI.db = new couch.Database(doc.db_name);
        UI.project = UI.db.get_sync(id);
        UI.project_id = id;
        
        console.log(UI.project);
        
        if (!UI.project.root_id){
            setTimeout(UI.view_clips, 30);
            alert("Hey, this looks like a new project; if you're new to novacut ping JamesMR on IRC and bug him about the lack of tutorials.");
            var node = {
                "_id": couch.random_id(), 
                "node": {
                    "src": [], 
                    "type": "sequence",
                }, 
                "type": "novacut/node"
            };
            UI.db.save(node);
            UI.project.root_id = node._id;
            UI.db.save(UI.project);
        }
        if (!UI.project.main_bucket){
            var doc = {};
            doc._id = couch.random_id();
            doc.nodes = [];
            doc.type = "novacut/bucket";
            UI.db.save(doc);
            UI.project.main_bucket = doc._id;
            UI.db.save(UI.project);
        }

        UI.clips = {};
        UI.clips.length = 0;

        UI.views = {};
        UI.views.render = $("render");
        
        UI.views.clips = $("clips");
        UI.views.clips.flow = function(list, instant){
            if (!list){
                list = [];
                for (var id in UI.clips){
                    if (id !== "length"){
                        list.push({
                            time: UI.clips[id].time,
                            count: UI.clips[id].count,
                            id: id,
                        });
                    }
                };
                list.sort(function(a, b){
                    if(a.time > b.time){
                        return 1;
                    }
                    return -1;
                });
                list = list.map(function(o){
                    return o.id
                });
                UI.views.clips.by_time = list;
                instant = true;
            }
            var width = UI.views.clips.clientWidth;
            var count = Math.floor(width/210);
            var padding = Math.round((width - count*192)/(count+1));
            if (list && list.forEach){
                list.forEach(function(id, i){
                    if (!instant){
                        UI.clips[id].moveTo((padding+192)*(i%count) + padding , 115*((i - i % count) / count) + 5);
                    }
                    else{
                        UI.clips[id].posX = (padding+192)*(i%count) + padding;
                        UI.clips[id].posY = 115*((i - i % count) / count) + 5;
                    }
                });
            }
            else {
                var i = 0;
                for (var c in UI.clips){
                    var clip = UI.clips[c];
                    if (c !== "length"){
                        clip.moveTo((padding+192)*(i%count) + padding , 115*((i - i % count) / count) + 5);
                        i++;
                    }
                }
            }
        }

        UI.views.bucket = $("bucket");

        UI.views.clips.ondragover = UI.on_dragover;
        UI.views.clips.ondrop = UI.on_drop;

        set_title('title', UI.project.title);
        UI.session = new couch.Session(UI.db, UI.on_new_doc);
        UI.session.start();
        
        window.addEventListener("resize", function(){
            UI.views.clips.flow(UI.views.clips.by_time);
        });
    },

    on_state_hashed: function(project_id, node_id, intrinsic_id) {
        console.log(['state_hashed', project_id, node_id, intrinsic_id].join(' '));
        // null for default settings_id:
        Hub.send('hash_job', intrinsic_id, null);
    },

    on_job_hashed: function(intrinsic_id, settings_id, job_id) {
        console.log(['job_hashed', intrinsic_id, settings_id, job_id].join(' '));
    },

    render: function() {
        $("render-btn").disabled = true;
        console.log('render');
        //Hub.send('render', UI.project._id, UI.project.root_id, null);
        Hub.send('hash_state', UI.project._id, UI.project.root_id);
    },

    on_render_finished: function(job_id, file_id) {
        UI.player.src = 'dmedia:' + file_id;
        UI.player.play();
        $("render-btn").disabled = false;
        console.log(job_id);
    },

    on_new_doc: function(doc) {
        if (doc._id == UI.project.root_id) {
            UI.sequence = new Sequence(UI.session, doc);
            //document.body.appendChild(UI.sequence.element);
            UI.scrubber = $('scrubber');
            UI.scrubber.onmousewheel = UI.on_mousewheel;
            UI.scrubber.onmousedown = UI.on_mousedown;
        }
        else if (doc._id == UI.project.main_bucket) {
            UI.bucket = new Bucket(UI.session, doc);
            if (doc.nodes.length < 1){
                UI.view_clips();
            }
        }
        else if (doc.type == "dmedia/file"){
            var clip = new Clip(UI.session, doc);
            UI.clips[doc._id] = clip;
            UI.clips.length += 1;
            UI.views.clips.appendChild(clip.element);
            UI.views.clips.flow();
            Thumbs.flush();
            if (!doc.framerate){
                doc.framerate = doc.meta.framerate;
                doc.duration = doc.meta.duration;
                UI.session.save(doc);
                UI.session.commit();
            }
        }
    },
    
    view: function(view){
        for (var v in UI.views){
            UI.views[v].classList.remove("show");
            if (view == v){
                UI.views[view].classList.add("show");
                console.log("changed view");
            }
        }
    },
    
    view_clips: function(){
        Thumbs.flush();
        var list = [];
        for (var id in UI.clips){
            if (id !== "length"){
                list.push({
                    time: UI.clips[id].time,
                    count: UI.clips[id].count,
                    id: id,
                });
            }
        };
        list.sort(function(a, b){
            if(a.time > b.time){
                return 1;
            }
            return -1;
        });
        list = list.map(function(o){
            return o.id
        });
        UI.views.clips.by_time = list;
        UI.views.clips.flow(list, true);
        UI.view("clips");
    },
    
    view_bucket: function(){
        UI.view("bucket");
    },
    
    view_render: function(){
        UI.view("render");
    },

    on_mousewheel: function(event) {
        $halt(event);
        var delta = wheel_delta(event) * (192 + 8);
        UI.sequence.element.scrollLeft += delta;
        UI.scrubber.style.setProperty("background-position", -UI.sequence.element.scrollLeft/2 + "px 0px");
    },
    
    on_mousedown: function(event) {
        $halt(event);
        UI.scrubber.offsetX = event.offsetX;
        var tmp = {};
        tmp.on_mousemove = function(event) {
            UI.on_mousemove(event);
        }
        tmp.on_mouseup = function(event) {
            window.removeEventListener('mousemove', tmp.on_mousemove);
            window.removeEventListener('mouseup', tmp.on_mouseup);
        }
        window.addEventListener('mousemove', tmp.on_mousemove);
        window.addEventListener('mouseup', tmp.on_mouseup);
    },
    
    on_mousemove: function(event) {
        $halt(event);
        var dist = (event.clientX - UI.scrubber.offsetX);
        if (event.shiftKey == true){
            dist *= 10;
        }
        UI.sequence.element.scrollLeft -= dist;
        UI.scrubber.offsetX = event.clientX;
        UI.scrubber.style.setProperty("background-position", -UI.sequence.element.scrollLeft + "px 0px");
    },
    
    on_dragover: function(event){
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
    },
    
    on_drop:  function(event){
        var data = event.dataTransfer.getData("Text").split("/");
        var id = data[1];
        var database = data[0];
        var tmp_db = new couch.Database(database);
        if (tmp_db.get_sync(id).type == "dmedia/file"){
            Hub.send('copy_docs', database, UI.project.db_name, [id]);
            setTimeout(function(){
                var list = [];
                for (var id in UI.clips){
                    if (id !== "length"){
                        list.push({
                            time: UI.clips[id].time,
                            count: UI.clips[id].count,
                            id: id,
                        });
                    }
                };
                list.sort(function(a, b){
                    if(a.time > b.time){
                        return 1;
                    }
                    return -1;
                });
                list = list.map(function(o){
                    return o.id
                });
                UI.views.clips.by_time = list;
                UI.views.clips.flow(UI.views.clips.by_time);
            }, 10);
        }
    },
    
    delete_project: function(){
        if (confirm("Delete this Project?\nNote: This is irreversable")){
            var tmp_db = new couch.Database("novacut-0");
            tmp_db.delete_sync(UI.project_id, {rev: tmp_db.get_sync(UI.project_id)._rev});
            UI.db.delete_sync();
            window.history.back();
        }
    },
    
    delete_slice: function(doc){
        if (doc.node && doc.node.type == "slice"){
            UI.db.delete_sync(doc._id, {rev: doc._rev});
        }
    },
    
    alert: function(msg){
        
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
