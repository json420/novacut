var sequence_viewer = function(session, doc){
    this.doc = doc;
    this.session = session;
    this.session.subscribe(doc._id, this.on_change, this);
    this.init = true;
    
    this.slices = [];
    this.index = 0;
    
    this.element = document.createElement("div");
    this.element.classList.add("seq-preview");
    
    this.video1 = document.createElement("video");
    //this.video1.muted = true;
    this.video2 = document.createElement("video");
    //this.video2.muted = true;
    this.video2.style.visibility = "visible";
    this.video2.visible = 1;
    
    this.element.appendChild(this.video1);
    this.element.appendChild(this.video2);
    
    this.on_change(this.doc);
    
    this.video1.src = "dmedia:" + this.session.get_doc(this.slices[1]).node.src;
    this.video2.src = "dmedia:" + this.session.get_doc(this.slices[0]).node.src;
    
    this.video1.addEventListener("canplaythrough", $bind(this.set_start, this));
    this.video2.addEventListener("canplaythrough", $bind(this.set_start, this));
    var watch = setInterval($bind(function(){
        if ((this.video2.visible && !this.video2.paused && this.video2.framerate && this.video2.currentTime * this.video2.framerate >= this.session.get_doc(this.slices[this.index%this.slices.length]).node.stop.frame) || (!this.video1.paused && this.video1.framerate && this.video1.currentTime * this.video1.framerate >= this.session.get_doc(this.slices[this.index%this.slices.length]).node.stop.frame)){
            this.play_next();
        }
    }, this), 10);
}
sequence_viewer.prototype = {
    on_change: function(doc){
        this.doc = doc;
        this.slices = [];
        this.doc.node.src.forEach($bind(function(src){
            var slicedoc = this.session.get_doc(src);
            this.slices.push(slicedoc._id);
        }, this));
    },
    flip: function(play){
        if (this.video2.visible){
            this.video2.pause();
            this.video2.style.visibility = "hidden";
            if (play){
                this.video1.play();
            }
            this.video2.visible = 0;
        }
        else{
            this.video1.pause();
            this.video2.style.visibility = "visible";
            if (play){
                this.video2.play();
            }
            this.video2.visible = 1;
        }
    },
    load_next: function(){
        if (this.video2.visible){
            this.video1.src = "dmedia:" + this.session.get_doc(this.slices[(this.index+1)%this.slices.length]).node.src;
        }
        else{
            this.video2.src = "dmedia:" + this.session.get_doc(this.slices[(this.index+1)%this.slices.length]).node.src;
        }
    },
    play_next: function(){
        this.index += 1;
        this.flip(1);
        this.load_next();
    },
    play: function(){
        if (this.video2.visible){
            this.video2.play();
        }
        else{
            this.video1.play();
        }
    },
    set_start: function(event){
        var clip = this.session.get_doc(event.target.src.replace("dmedia:", ""));
        event.target.framerate = clip.framerate.num/clip.framerate.denom;
        if (this.init && event.target === this.video2){
            event.target.currentTime = this.session.get_doc(this.slices[0]).node.start.frame / event.target.framerate;
            this.init = false;
        }
        else{
            event.target.currentTime = this.session.get_doc(this.slices[(this.index + 1)%this.slices.length]).node.start.frame / event.target.framerate;
        }
    },
}
