var slice_viewer = function(session, doc){
    this.doc = doc;
    this.session = session;
    this.session.subscribe(doc._id, this.on_change, this);
    
    this.element = document.createElement("div");
    this.element.classList.add("sli-preview");
    
    this.video = document.createElement("video");
    //this.video.muted = true;
    
    this.element.appendChild(this.video);
    
    this.on_change(this.doc);
    this.video.addEventListener("canplaythrough", $bind(this.set_start, this));
    
    this.interval = setInterval($bind(this.watch, this), 10);
}
sequence_viewer.prototype = {
    on_change: function(doc){
        this.doc = doc;
        if (this.doc.node.src != this.video.src.replace("dmedia:", "")){
            this.video.src = "dmedia:" + this.doc.node.src;
        }
    },
    play: function(){
        this.video.play();
    },
    set_start: function(){
        this.video.framerate = this.doc.framerate.num/this.doc.framerate.denom;
        this.video.currentTime = this.doc.node.start.frame / this.video.framerate;
    },
    watch: function(){
        if (!this.video.paused && this.video.framerate && this.video.currentTime * this.video.framerate >= this.doc.node.stop.frame)){
            this.video.pause();
        }
    }
}
