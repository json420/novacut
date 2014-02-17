"use strict";

function open_project(project_id) {
    window.location.assign('cutter.html#' + project_id); 
}

function countFiles(project_id){
	var pdb = new couch.Database("novacut-1-" + project_id.toLowerCase());
	try{
	    var filecount = pdb.view_sync('doc', 'type', {key: 'dmedia/file'}).rows[0].value;
	}
	catch(e){
	    var filecount = 0;
	}
	return filecount;
}

function getOffset( el ) {//get the coordinates of an element
    var _x = 0;
    var _y = 0;
    while( el && !isNaN( el.offsetLeft ) && !isNaN( el.offsetTop ) ) {
        _x += el.offsetLeft - el.scrollLeft;
        _y += el.offsetTop - el.scrollTop;
        el = el.offsetParent;
    }
    return { y: _y, x: _x };
}

function generateAnimation(x,y){//generate the animation for the elimination of a project
	var keyframeprefix = "-webkit-";
	var keyframes = '@' + keyframeprefix + 'keyframes arg { '+'0% {' + keyframeprefix + 'transform:scale(1)}'+'100% {' + keyframeprefix + 'transform:translatex('+x+'px) translatey('+y+'px) scale(0.001)}'+'}';
	var s = document.createElement( 'style' );
	s.innerHTML = keyframes;
	document.getElementsByTagName( 'head' )[ 0 ].appendChild( s );
}

var UI = {
    init: function() {
        UI.form = $('new_project');
        UI.input = UI.form.getElementsByTagName('input')[0];
        UI.button = UI.form.getElementsByTagName('button')[0];
        
        UI.form.onsubmit = UI.on_submit;
        UI.input.oninput = UI.on_input;
        
	UI.hist = document.getElementById('list');
	UI.proj = document.getElementById('projects');
	UI.proj.style.height = window.innerHeight-50+"px";


	UI.binDesc ="<p>Here You Can Find Your Removed Projects<br>Click on <img style=\"width:13px;\" src=\"delete.png\"></img>&nbsp;&nbsp;&nbsp;to Remove a Project<br>Drag a Project Out of Here to Restore It</p>";
	UI.binMax = 5;
	UI.binSearch = "<input id=\"s\" onkeyup=\"UI.Search()\" autofocus/><p id='help'>To restore a project drag it out of here</p>";

	UI.removed = new Array();
        UI.load_items();
    },

    load_items: function() {
        console.log('load_items');
        novacut.view(UI.on_items, 'project', 'title');
    },

    on_items: function(req) {
        var rows = req.read().rows;
        console.log(rows.length);
	for(var b in rows){
		var a = rows[b];
		var filecount = countFiles(a.id);
		var doc = novacut.get_sync(a.id);
		if(!doc.isdeleted) UI.add_item(a.id,a.key,a.value,filecount);
		else UI.removed.push(Array(a.id,a.key,a.value,filecount));
	}
	if(UI.removed.length == 0){
		document.getElementById("cont").innerHTML=UI.binDesc;	
	}else if(UI.removed.length <= UI.binMax){
		for(var b in UI.removed){
			var a = UI.removed[b];
			UI.add_history(a[0],a[1],a[2],a[3]);
		}

	}else{
		document.getElementById("cont").innerHTML = UI.binSearch;
		for(var b = 0;b<UI.binMax;b++){
			var a = UI.removed[b];
			UI.add_history(a[0],a[1],a[2],a[3]);
		}
	} 
    },

    Search: function(){
	var text = document.getElementById("s").value;
	UI.hist.innerHTML = "";
	var count = 0;
	for(var b in UI.removed){
		var a = UI.removed[b];
		if(a[1].indexOf(text) != -1){
			count++;
			UI.add_history(a[0],a[1],a[2],a[3]);
			if(count == UI.binMax)break;
		}
	} 
    },

    add_history: function(id,name,date,filecount){
                var li = $el('li', {'class': 'project', 'id': id});
		li.setAttribute('draggable', 'true');
		li.setAttribute('ondragstart', 'dragstart(event)');
                var thumb = $el('div', {'class': 'thumbnail'});
                thumb.style.backgroundImage = "url(/_apps/dmedia/novacut-avatar-192.png)";//novacut.att_css_url(row.id);

                var info = $el('div', {'class': 'info'});
                info.appendChild(
                    $el('p', {'textContent': name, 'class': 'title'})
                );

                info.appendChild(
                    $el('p', {'textContent': format_date(date)})
                );

                info.appendChild(
                    $el('p', {'textContent': filecount + ' files'})
                );

                li.appendChild(thumb);
                li.appendChild(info);
		UI.hist.appendChild(li);
    },
    add_item: function(id,name,date,filecount) {
                var li = $el('li', {'class': 'project', 'id': id});
                var thumb = $el('div', {'class': 'thumbnail'});
                thumb.style.backgroundImage = "url(/_apps/dmedia/novacut-avatar-192.png)";//novacut.att_css_url(row.id);

                var info = $el('div', {'class': 'info'});
                info.appendChild(
                    $el('p', {'textContent': name, 'class': 'title'})
                );

                info.appendChild(
                    $el('p', {'textContent': format_date(date)})
                );

                info.appendChild(
                    $el('p', {'textContent': filecount + ' files'})
                );

                li.appendChild(thumb);
                li.appendChild(info);
		var del=document.createElement("img");
		del.setAttribute('src', 'delete.png');
		del.setAttribute('align', 'right');
		del.onclick = function(){
   		    var pos = getOffset(this.parentNode);
		    var end = getOffset( document.getElementById("ico"));
		    generateAnimation(end.x-pos.x,end.y-pos.y-30);
		    this.parentNode.style.webkitAnimationName = "arg";
		    var s = this;
		    setTimeout(function(){s.parentNode.parentNode.removeChild(s.parentNode)},300,s);
 		    Hub.send('delete_project', id)
		    var doc = novacut.get_sync(id)
		    UI.removed.push(Array(id,doc.title,doc.time,countFiles(id)));
		    document.getElementById("cont").innerHTML = "";
		    if (UI.removed.length > UI.binMax) document.getElementById("cont").innerHTML = UI.binSearch;
		    else UI.add_history(id,doc.title,doc.time,countFiles(id));
		}
		li.appendChild(del);
                thumb.onclick = function() {
                    Hub.send('load_project', id)
                }
                info.onclick = function() {
                    Hub.send('load_project', id)
                }
		UI.proj.appendChild(li);
    },

    on_input: function(event) {
        UI.button.disabled = (!UI.input.value);
    },

    on_submit: function(event) {
        event.preventDefault();
        event.stopPropagation();
        if (UI.input.value) {
            var title = UI.input.value;
            UI.input.value = '';
            UI.button.disabled = true;
            Hub.send('create_project', title);
        }
    },
}


window.addEventListener('load', UI.init);


function dragstart(ev){
       ev.dataTransfer.setData("Text", ev.target.id);
    ev.dataTransfer.effectAllowed = 'move';
}
function enter(ev){
        ev.preventDefault();
    //ev.target.setAttribute("style","cursor: ;");
    return false;
}
function leave(ev){
    return false;
}
function d(ev){
        ev.preventDefault();
    var data=ev.dataTransfer.getData("Text");
    Hub.send('sos_project', data);
    element = document.getElementById(data);
    element.parentNode.removeChild(element);
    var doc = novacut.get_sync(data)        
    UI.add_item(data,doc.title,doc.time,countFiles(data));
    var old = UI.removed.length;
    for(var b in UI.removed){//remove the project from the list
        if(UI.removed[b][0] == data){
            UI.removed.splice(b,1);
            break;
        }
    }
    if(UI.removed.length == 0)document.getElementById("cont").innerHTML=UI.binDesc;
    else if(UI.removed.length > UI.binMax)UI.add_history(UI.removed[UI.binMax-1][0],UI.removed[UI.binMax-1][1],UI.removed[UI.binMax-1][2],UI.removed[UI.binMax-1][3]);
    if(UI.removed.length == UI.binMax){
        document.getElementById("cont").innerHTML="";
        document.getElementById("list").innerHTML="";
        for(var b = 0;b<UI.binMax;b++){
            var a = UI.removed[b];
            UI.add_history(a[0],a[1],a[2],a[3]);
        }
    }
    return false;
}
function over(ev){
       ev.preventDefault();
}
