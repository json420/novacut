"use strict";


function open_project(project_id) {
    window.location.assign('cutter.html#' + project_id); 
}

function countFiles(project_id){
	var pdb = new couch.Database("novacut-0-" + project_id.toLowerCase());
	try{
	    var filecount = pdb.view_sync('doc', 'type', {key: 'dmedia/file'}).rows[0].value;
	}
	catch(e){
	    var filecount = 0;
	}
	return filecount;
}

var UI = {
    init: function() {
        UI.form = $('new_project');
        UI.input = UI.form.getElementsByTagName('input')[0];
        UI.button = UI.form.getElementsByTagName('button')[0];
        //UI.project = new Project(novacut);
        //UI.items = new Items('projects');
        
        UI.form.onsubmit = UI.on_submit;
        UI.input.oninput = UI.on_input;
        
	UI.hist = document.getElementById('list');
	UI.proj = document.getElementById('projects');
        UI.load_items();
    },

    load_items: function() {
	//UI.add_history("qwe","nome",3333,3);
        console.log('load_items');
        novacut.view(UI.on_items, 'project', 'title');
    },

    on_items: function(req) {
        var rows = req.read().rows;
        console.log(rows.length);
	for(var b in rows){
		var a = rows[b]
		var pdb = new couch.Database("novacut-0-" + a.id.toLowerCase());
		try{
		    var filecount = pdb.view_sync('doc', 'type', {key: 'dmedia/file'}).rows[0].value;
		}
		catch(e){
		    var filecount = 0;
		}
		var doc = novacut.get_sync(a.id)
		if(!doc.isdeleted) UI.add_item(a.id,a.key,a.value,filecount);
		else UI.add_history(a.id,a.key,a.value,filecount);
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
		    this.parentNode.parentNode.removeChild(this.parentNode);
 		    Hub.send('delete_project', id)
		    var doc = novacut.get_sync(id)
		    UI.add_history(id,doc.title,doc.time,countFiles(id));
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
