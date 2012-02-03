/*

 -- Copy media into the project database -- 
Hub.send('copy_docs', src_db, dst_db, docs_ids);

novacut-0 lists projects

novacut-0-ID is a project database

novacut.view(callback, "project", "title") gets the project ids by title

project.view(callback, "node", "type", {key: "sequence"});

*/

var getHashList, sortcontainer;

"use strict";

function getOffset(e){e=e.offsetParent;p=[0,0];while(e!=null){p[0]+=e.offsetLeft;p[1]+=e.offsetTop;e=e.offsetParent}return p;}

var dmedia = new couch.Database("dmedia");
var thumbnails = new couch.Database("thumbnails");

function Clip(id){
    var self = this;
    self.element = document.createElement("div");
    self.element.classList.add("sorting-clip");
    self.element.dataset.id = id;
    self.id = id;
    self.element.style.setProperty("background", "url(" + dmedia.att_url(id, 'thumbnail') + ")");
    self.element.style.setProperty("z-index", 10);
    self.sortcontainer = document.getElementById("sort-container");
    self.info = document.createElement("div");
    self.info.classList.add("info");
    self.info.textContent = "no data";
    self.doc = db.get_sync(self.id);
    self.element.appendChild(self.info);
    self.btn_edit = document.createElement("div");
    self.btn_edit.classList.add("edit");
    self.btn_edit.clicked = false;
    self.btn_edit.onmousedown = function(){
        self.view();
    }
    self.element.appendChild(self.btn_edit);
    
    self.oldpos = [0,0];
    
    self.posX = 0;
    self.posY = 0;
    
    self.drawInfo = function(){
        if (self.doc.meta){
            var time = self.doc.meta.duration;
            if (!time){
                time = 0;
            }
        }
        else if (self.doc.duration){
            var time = Math.round(self.doc.duration.seconds);
        }
        else{
            var time = 0;
        }
        if (time > 3600){
            var h = (time - (time % 60))/60;
            time -= h * 3600;
            if (h < 10){
                h = "0" + h;
            }
        }
        else{
            var h = "00";
        }
        if (time > 60){
            var m = (time - (time % 60))/60;
            time -= m * 60;
            if (m < 10){
                m = "0" + m;
            }
        }
        else{
            var m = "00";
        }
        if (time < 10){
            var s = "0" + time;
        }
        else{
            var s = time;
        }
        var slices = db.view_sync("node", "src", {key: self.doc._id, reduce: false}).rows.length;
        self.info.textContent = slices + " Slice " + h + ":" + m + ":" + s + "s";
    }
    
    self.drawInfo();
    
    self.addTo = function(parent){
        parent.appendChild(self.element);
    }
    
    self.remove = function(){
        self.element.parentElement.removeChild(self.element);
    }
    
    self.moveTo = function(x,y){
        dx = (x - self.posX)/2;
        dy = (y - self.posY)/2;
        
        if (dx > 0){
            self.posX += Math.ceil(dx);
        }
        else{
            self.posX += Math.floor(dx);
        }
        
        
        if (dy > 0){
            self.posY += Math.ceil(dy);
        }
        else{
            self.posY += Math.floor(dy);
        }
        if (self.posX != x || self.posY != y){
            setTimeout(function(){
                self.moveTo(x, y);
            }, 40);
        }
    }
    
    self.element.addEventListener("mousedown", function(event){
        self.view(event);
        return;
        /*if (event.button == 2 || self.btn_edit.clicked == true){
            self.btn_edit.clicked = false;
            return;
        }
        event.preventDefault();
        self.mousedown = true;
        self.oldpos = [self.posX, self.posY];
        if (self.element.parentElement == self.sortcontainer){
            self.old = getOffset(self.element);
            self.offset = [event.offsetX, event.offsetY];
            if (event.target.classList.contains("info") == true){
                self.offset = [self.offset[0], self.offset[1] + self.element.clientHeight - event.target.clientHeight]
            }
        }
        else{
            setTimeout(function(){
                self.offset = [self.element.clientWidth/2, self.element.clientHeight/2];
            }, 1);
        }
        
        self.element.style.setProperty("position", "absolute");
        self.element.style.setProperty("z-index", 9999);
        self.oldparent = self.element.parentElement;
        self.remove();
        self.element.classList.add("moving");
        self.addTo(document.body);
        self.posX = event.clientX - self.offset[0];
        self.posY = event.clientY - self.offset[1];
        
        self.target = undefined;
        
        document.addEventListener("mousemove", function(event){
            if (self.mousedown == true){
                self.posX = event.clientX - self.offset[0];
                self.posY = event.clientY - self.offset[1];
                if (event.clientY > document.height - document.getElementById("buckets").clientHeight){
                    targets = buckets.getElementsByClassName("bucket");
                    for (i = 0; i < targets.length; i++){
                        target = targets[i];
                        if (event.clientX > target.offsetLeft - buckets.scrollLeft && event.clientX < target.offsetLeft - buckets.scrollLeft + target.clientWidth && event.clientY > document.height - document.getElementById("buckets").clientHeight + target.offsetTop){
                            if (target.dataset.id){
                                self.target = target.dataset.id;
                                target.classList.add("target");
                            }
                            if (self.target == undefined){
                                target.classList.remove("target");
                            }
                        }
                        else{
                            target.classList.remove("target");
                        }
                    }
                }
                else{
                    self.target = undefined;
                }
            }
        });
        
        document.addEventListener("mouseup", function(event){
            if (self.mousedown == true){
                self.mousedown = false;
                self.remove();
                self.element.classList.remove("moving");
                dropPos = [event.clientX, event.clientY];
                if (self.target){
                    bucketlist.forEach(function(bucket){
                        if (bucket.id == self.target){
                            self.addTo(bucket.container);
                            self.element.style.setProperty("position", "static");
                            self.element.style.setProperty("z-index", 10);
                            self.posX = 0;
                            self.posY = 0;
                            bucket.element.classList.remove("target");
                            bucket.scrollDown();
                        }
                    });
                }
                else{
                    self.addTo(self.sortcontainer);
                    self.element.style.setProperty("z-index", 10);
                    self.posX -= self.old[0];
                    self.posY -= self.old[1];
                    if (event.clientY > document.height - document.getElementById("buckets").clientHeight){
                        self.moveTo(self.oldpos[0], self.oldpos[1]);
                    }
                }
            }
        });*/
    });
    
    self.view = function(event){
        if (event){
            event.preventDefault();
        }
        if (!slices[self.id]){
            slices[self.id] = [];
        }
        slicelist.textContent = "";
        var rows = db.view_sync("node", "src", {reduce: false, key: self.id, include_docs: true}).rows;
        rows.forEach(function(row){
            var found = false;
            slices[self.id].forEach(function(s){
                if (s.id == row.id){
                    found = true;
                    s.addTo(slicelist);
                }
            });
            if (found == false){
                slices[self.id].push(new Slice(row.id));
                slices[self.id][slices[self.id].length - 1].addTo(slicelist);
            }
        });
        clipview.classList.add("show");
        preview_info.textContent = self.doc.name;
        preview.src = "dmedia:" + self.id;
        preview.load();
        preview_prog.style.setProperty("width", "0%");
        document.getElementsByClassName("slicecontrols")[0].classList.remove("show");
        preview.dataset.id = self.id;
        
    }
    
    self.element.addEventListener("contextmenu", self.view);
}


Clip.prototype = {
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
    }
}

function Slice(id){
    var self = this;
    var doc = db.get_sync(id);
    if (doc.type == "dmedia/file"){
        self.newslice = true;
        self.id = couch.random_id();    
        self.clipid = id;
        self.doc = {
            "_id": self.id,
            "node": {
                "src": self.clipid,
                "start": {
                    "frame": 0
                },
                "stop": {
                    "frame": 100
                },
                "stream": "video",
                "type": "slice"
            },
            "type": "novacut/node"
        };
        db.save(self.doc);
    }
    else if (doc.type == "novacut/node"){
        self.doc = doc;
        self.clipid = self.doc.node.src;
        self.id = self.doc._id;
    }
    self.element = document.createElement("div");
    self.element.classList.add("slice");
    self.element.dataset.id = id;
    self.clipview = document.getElementById("slices");
    self.clipdoc = db.get_sync(self.clipid);
    
    
    
    self.startframe = document.createElement("div");
    self.startframe.classList.add("frame");
    self.startframe.style.setProperty("background", "url(" + thumbnails.att_url(self.clipid, self.doc.node.start.frame) + ")");
    self.element.appendChild(self.startframe);
    
    self.stopframe = document.createElement("div");
    self.stopframe.classList.add("frame");
    self.stopframe.style.setProperty("background", "url(" + thumbnails.att_url(self.clipid, self.doc.node.stop.frame) + ")");
    self.element.appendChild(self.stopframe);
    
    self.btn_edit = document.createElement("div");
    self.btn_edit.classList.add("edit");
    self.btn_edit.clicked = false;
    self.btn_edit.onmousedown = function(){
        //Edit slice!
    }
    self.element.appendChild(self.btn_edit);

    self.oldpos = [0,0];
    self.posX = 0;
    self.posY = 0;
    
    self.addTo = function(parent){
        parent.appendChild(self.element);
    }
    
    self.remove = function(){
        self.element.parentElement.removeChild(self.element);
    }
    
    self.moveTo = function(x,y){
        dx = (x - self.posX)/2;
        dy = (y - self.posY)/2;
        if (dx > 0){
            self.posX += Math.ceil(dx);
        }
        else{
            self.posX += Math.floor(dx);
        }
        if (dy > 0){
            self.posY += Math.ceil(dy);
        }
        else{
            self.posY += Math.floor(dy);
        }
        if (self.posX != x || self.posY != y){
            setTimeout(function(){
                self.moveTo(x, y);
            }, 40);
        }
    }
    
    self.element.addEventListener("mousedown", function(event){
        event.preventDefault();
        if (event.shiftKey == false){
            slices[self.clipid].forEach(function(s){
                if (s.selected == true){
                    s.selected = false;
                }
            });
            self.selected = true;
            loadSlice(self, self.doc);
        }
        else{
            if (self.selected == true){
                self.selected = false;
            }
            else{
                self.selected = true;
                loadSlice(self, self.doc);
            }
        }
        
    });
    
    self.element.addEventListener("contextmenu", function(event){
        event.preventDefault();
    });
}


Slice.prototype = {
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
    get selected(){
        return this.element.classList.contains("selected");
    },
    set selected(value){
        if (value == true){
            this.element.classList.add("selected");
        }
        else if (value == false){
            this.element.classList.remove("selected");
        }
    },
    get start(){
        return this.doc.node.start.frame;
    },
    set start(val){
        this.doc.node.start.frame = parseInt(val);
        var controls = document.getElementsByClassName("slicecontrols")[0]
        var startel = controls.getElementsByClassName("start")[0]
        startel.dataset.frame = val;
        startel.style.setProperty("left", val/(preview.duration*30)*100 + "%");
        this.save();
    },
    get stop(){
        return this.doc.node.stop.frame;
    },
    set stop(val){
        this.doc.node.stop.frame = parseInt(val);
        var controls = document.getElementsByClassName("slicecontrols")[0]
        var stopel = controls.getElementsByClassName("stop")[0]
        stopel.dataset.frame = val;
        stopel.style.setProperty("left", val/(preview.duration*30)*100 + "%");
        this.save();
    },
    save: function(){
        db.save(this.doc);
    }
}

function Bucket(){
    var self = this;
    self.element = document.createElement("div");
    self.element.classList.add("bucket");
    self.element.dataset.id = Math.floor(Math.random()*1000000);
    
    self.id = self.element.dataset.id;
    
    self.name = prompt("Bucket name:");
    
    self.container = document.createElement("div");
    self.container.classList.add("container");
    
    self.controls = document.createElement("div");
    self.controls.classList.add("controls");
    self.controls.innerHTML = "<div class=\"delete\"></div>"
    
    self.element.appendChild(self.controls);
    self.element.appendChild(self.container);
    
    self.controls.onclick = function(event){
        event.preventDefault();
        if (event.target.classList.contains("delete") == true){
            self.remove();
        }
        
    }
    
    self.scrollDown = function(){
        var pos = self.container.scrollTop;
        var maxpos = self.container.scrollHeight - self.container.clientHeight;
        self.container.scrollTop += Math.ceil((maxpos - pos)/2);
        if (self.container.scrollTop < self.container.scrollHeight - self.container.clientHeight){
            setTimeout(self.scrollDown, 40);
        }
    }
    
    self.clips = [];
    
    self.addClip = function(id){
        var img = document.createElement("div");
        img.classList.add("clip");
        img.style.setProperty("background", "url("+id+")");
        self.container.appendChild(img);
        self.scrollDown();
    }
    
    self.addTo = function(parent){
        parent.appendChild(self.element);
    }
    
    self.remove = function(){
        self.element.parentElement.removeChild(self.element);
    }
}

Bucket.prototype = {
    get name(){
        return this.element.dataset.name;
    },
    set name(value){
        this.element.dataset.name = value;
    }
}

window.onload = function(){
    /*document.getElementById("browser").onclick = function(event){
        if (event.target.classList.contains("grip") == true){
            if (browser.classList.contains("open") == true){
                this.classList.remove("open");
            }
            else this.classList.add("open");
        }
    }*/
    
    sortcontainer = document.getElementById("sort-container");
    sortcontainer.ondragover = function(event){
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
    }
    sortcontainer.ondrop = function(event){
        var data = event.dataTransfer.getData("Text").split("/");
        var id = data[1];
        var database = data[0];
        Hub.send('copy_docs', database, db.name, [id]);
        clips[id] = new Clip(id);
        clips[id].addTo(sortcontainer);
        clips[id].posX = event.clientX;
        clips[id].posY = event.clientY-24;
    }
    
    preview = document.getElementById("sort-preview-video");
    preview_info = document.getElementById("sort-preview").getElementsByClassName("info")[0];
    preview_prog = document.getElementById("sort-preview").getElementsByClassName("progress")[0];
    prevprog = function(){
        pos = preview.currentTime / preview.duration;
        preview_prog.style.setProperty("width", pos*100 + "%");
        if (document.getElementsByClassName("slicecontrols")[0].classList.contains("show") == true && preview.paused == false){
            if (preview.getFrame() >= preview.selected.stop){
                preview.setFrame(preview.selected.start);
            }
        }
        if (preview.paused == false){
            setTimeout(prevprog, 33);
        }
    }
    preview.onclick = function(){
        if (preview.paused == false){
            preview.pause();
        }
        else{
            preview.play();
            prevprog();
        }
    }
    preview.setFrame = function(f){
        this.currentTime = f/30;
    }
    preview.getFrame = function(){
        return Math.floor(this.currentTime * 30);
    }
    preview.getFrames = function(){
        return Math.floor(this.duration*30);
    }
    
    slicelist = document.getElementById("slices");
    createslice = document.getElementById("createslice");
    createslice.onclick = function(event){
        event.preventDefault();
        var id = preview.dataset.id;
        if (slices[id]){
            slices[id].push(new Slice(id));
        }
        else{
            slices[id] = [];
            slices[id].push(new Slice(id));
        }
        slices[id][slices[id].length-1].stop = preview.getFrames();
        slices[id][slices[id].length-1].addTo(slicelist);
        clips[id].drawInfo();
    }
    
    buckets = document.getElementById("buckets");
    buckets.onmousewheel = function(event){
        if (event.wheelDelta < 0){
            buckets.scrollLeft += 30;
        }
        else if (event.wheelDelta > 0){
            buckets.scrollLeft -= 30;
        }
    }
    
    clipview = document.getElementById("clip-view");
    clipview.onmousedown = function(event){
        if (event.target.id == "clip-view"){
            this.classList.remove("show");
            preview.pause();
        }
    }
    document.onkeypress = function(event){
        if (event.keyCode == 27){
            if (clipview.classList.contains("show") == true){
                clipview.classList.remove("show");
            }
        }
    }
    
    
    previewresize = document.getElementById("sort-preview").getElementsByClassName("v-thumb")[0];
    previewresize.onmousedown = function(event){
        var prevsize_last = event.clientX;
        mousedown = true;
        var resize = function(event){
            if (mousedown === true){
                var dist = event.clientX - prevsize_last;
                var current = parseInt(previewresize.parentElement.clientWidth);
                var size = current + dist;
                previewresize.parentElement.style.setProperty("width", size + "px");
                prevsize_last = event.clientX;
            }
        }
        document.body.addEventListener("mousemove", resize);
        document.body.addEventListener("mouseup", function(){
            document.body.removeEventListener("mousemove", resize);
            slicelist.style.setProperty("left", previewresize.parentElement.clientWidth + "px");
        });
    }
    
    starthandle = document.getElementsByClassName("slicecontrols")[0].getElementsByClassName("start")[0];
    stophandle = document.getElementsByClassName("slicecontrols")[0].getElementsByClassName("stop")[0];
    starthandle.addEventListener("mousedown", function(event){
        var self = this;
        if (preview.paused === false){
            self.play = true;
            preview.pause();
            preview.setFrame(preview.selected.start);
        }
        var move = function(event){
            var frames = Math.floor((event.clientX/preview.clientWidth)*preview.duration*30);
            if (frames > preview.selected.stop){
                frames = preview.selected.stop;
            }
            else if (frames < 0){
                frames = 0;
            }
            preview.selected.start = frames;
            preview.setFrame(preview.selected.start);
            prevprog();
        }
        document.addEventListener("mousemove", move);
        var mouseup = function(){
            document.removeEventListener("mousemove", move);
            document.removeEventListener("mouseup", mouseup);
            preview.setFrame(preview.selected.start);
            prevprog();
            if (self.play === true){
                preview.play();
            }
        }
        document.addEventListener("mouseup", mouseup);
    });
    stophandle.addEventListener("mousedown", function(event){
        var self = this;
        if (preview.paused === false){
            self.play = true;
            preview.pause();
        }
        else{
            self.play = false;
        }
        preview.setFrame(preview.selected.stop);
        var move = function(event){
            pos = event.clientX;
            var frames = Math.floor((event.clientX/preview.clientWidth)*preview.duration*30);
            if (frames < preview.selected.start){
                frames = preview.selected.start;
            }
            else if (frames > preview.getFrames()){
                frames = preview.getFrames();
            }
            preview.selected.stop = frames;
            preview.setFrame(preview.selected.stop);
            prevprog();
        }
        document.addEventListener("mousemove", move);
        var mouseup = function(){
            document.removeEventListener("mousemove", move);
            document.removeEventListener("mouseup", mouseup);
            preview.setFrame(preview.selected.stop);
            prevprog();
            if (self.play === true){
                preview.play();
                self.play = false;
            }
        }
        document.addEventListener("mouseup", mouseup);
    });
    
    clips = {};
    bucketlist = [];
    slices = {};
    
    /*document.getElementById("add-bucket").onclick = function(event){
        event.preventDefault();
        if (event.button == 0){
            bucketlist.push(new Bucket());
            bucketlist[bucketlist.length-1].addTo(buckets);
            
        }
        else if (event.button == 1){
            for (i = 0; i < 6; i++){
                setTimeout(function(){
                    var row = Math.floor(Math.random()*rows.length);
                    clips.push(new Clip(rows[row].id));
                    clips[clips.length-1].addTo(sortcontainer);
                    clips[clips.length-1].moveTo(Math.floor(Math.random()*(sortcontainer.clientWidth - 192)), Math.floor(Math.random()*(sortcontainer.clientHeight - 108)));
                }, i*50);
            }
        }
    }*/
    
    document.onmousedown = function(e){e.preventDefault()}
    
    window.onresize = function(){
        var i = 0;
        for (var id in clips){
            var clip = clips[id];
            
            var width = sortcontainer.clientWidth;
            var count = Math.floor(width/210);
            var padding = Math.round((width - count*192)/(count+1));
            
            clip.moveTo((padding+192)*(i%count) + padding , 115*((i - i % count) / count) + 5);
            i++;
            /*var clip = clips[id];
            if (clip.posX > window.innerWidth - 192){
                var x = window.innerWidth - 192;
                var move = true;
            }
            else{
                var x = clip.posX;
            }
            if (clip.posY > window.innerHeight - 325){
                var y = window.innerHeight - 325;
                var move = true;
            }
            else{
                var y = clip.posY;
            }
            if (move === true){
                clip.moveTo(x, y);
            }
            
            if (previewresize.parentElement.clientWidth > window.innerWidth){
                previewresize.parentElement.style.setProperty("width", window.innerWidth + "px");
                slicelist.style.setProperty("left", window.innerWidth + "px")
            }*/
        }
    }
    
    loadSlice = function(self, doc){
        if (doc.node.type == "slice"){
            self.start = doc.node.start.frame;
            self.stop = doc.node.stop.frame;
            preview.currentTime = self.start/30;
            preview.dataset.sliceid = self.id;
            document.getElementsByClassName("slicecontrols")[0].classList.add("show");
            slices[preview.dataset.id].forEach(function(s){
                if (s.id == preview.dataset.sliceid){
                    preview.selected = s;
                }
            });
            prevprog();
        }
    }
    
    var projects = new couch.Database("novacut-0");
    
    projects.view(function(req){
        var list = req.read().rows;
        list.forEach(function(project){
            var a = document.createElement("a");
            a.textContent = project.key;
            sortcontainer.appendChild(a);
            a.dataset.id = project.id.toLowerCase();
            sortcontainer.innerHTML += "<br/>";
        });
        var links = sortcontainer.getElementsByTagName("a");
        for (var i = 0; i < links.length; i++){
            var link = links[i];
            link.onmousedown = function(){
                db = "novacut-0-" + this.dataset.id;
                db = new couch.Database(db);
                root_id = db.get_sync(this.dataset.id.toUpperCase()).root_id;
                rows = db.view_sync("doc", "type", {key: 'dmedia/file', reduce: false}).rows;
                sortcontainer.textContent = "";
                var width = sortcontainer.clientWidth;
                var count = Math.floor(width/210);
                var padding = Math.round((width - count*192)/(count+1));
                rows.forEach(function(doc, i){
                    setTimeout(function(){
                        clips[doc.id] = new Clip(doc.id);
                        clips[doc.id].addTo(sortcontainer);
                        clips[doc.id].moveTo((padding+192)*(i%count) + padding , 115*((i - i % count) / count) + 5);
                    }, 50*i);
                });
                setTimeout(function(){
                    root_node = db.get_sync(root_id);
                    root_node.node.src.forEach(function(src){
                        var doc = db.get_sync(src);
                        if (!slices[doc.node.src]){
                            slices[doc.node.src] = [];
                        }
                        slices[doc.node.src].push(new Slice(doc._id));
                        
                }, 0);
                });
            }
        }
        
    }, "project", "title");
    
}

getHashList = function(){return window.location.hash.slice(1).split("/")};
setHashList = function(l){window.location.hash = l.join("/")};

window.onhashchange = function(e){
    var old_hash = e.oldURL.split("#").slice(1).join("#");
    var new_hash = e.newURL.split("#").slice(1).join("#");
    console.log(old_hash);
    console.log(new_hash);
}

var canvas = document.createElement("canvas");
canvas.width = 224;
canvas.height = 222;
context = canvas.getContext("2d");
context.fillStyle = "rgba(10, 5, 2, 0.9)";
context.fillRect(0, 0, 224, 222);
i = 2;
while (i < 222){
    context.clearRect(4, i, 8, 8);
    context.clearRect(212, i, 8, 8);
    i += 15;
}
var slicebg = canvas.toDataURL("image/png");
var style = document.createElement("style");
style.textContent = ".slice{background:url('" + slicebg + "')}";
document.head.appendChild(style);
