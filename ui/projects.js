"use strict";


function open_project(project_id) {
    window.location.assign('cutter.html#' + project_id); 
}


var UI = {
    init: function() {
        UI.form = $('new_project');
        UI.input = UI.form.getElementsByTagName('input')[0];
        UI.button = UI.form.getElementsByTagName('button')[0];
        UI.project = new Project(novacut);
        UI.items = new Items('projects');
        
        UI.form.onsubmit = UI.on_submit;
        UI.input.oninput = UI.on_input;
        
        UI.load_items();
    },

    load_items: function() {
        console.log('load_items');
        novacut.view(UI.on_items, 'project', 'title');
        history.view(UI.on_history, 'project', 'title');
    },

    on_history: function(req){
	var rows = req.read().rows;
	console.log(rows.length);
	var his = new Items('list');
	his.replace(rows,
		function(row, items) {
		var pdb = new couch.Database("novacut-0-" + row.id.toLowerCase());
		try{
		    var filecount = pdb.view_sync('doc', 'type', {key: 'dmedia/file'}).rows[0].value;
		}
		catch(e){
		    var filecount = 0;
		}
            
                var li = $el('li', {'class': 'project', 'id': row.id});
		li.setAttribute('draggable', 'true');
		li.setAttribute('ondragstart', 'dragstart(event)');
                var thumb = $el('div', {'class': 'thumbnail'});
                thumb.style.backgroundImage = "url(/_apps/dmedia/novacut-avatar-192.png)";//novacut.att_css_url(row.id);

                var info = $el('div', {'class': 'info'});
                info.appendChild(
                    $el('p', {'textContent': row.key, 'class': 'title'})
                );

                info.appendChild(
                    $el('p', {'textContent': format_date(row.value)})
                );

                info.appendChild(
                    $el('p', {'textContent': filecount + ' files'})
                );

                li.appendChild(thumb);
                li.appendChild(info);

                return li;
            }
        );
    },

    on_items: function(req) {
        var rows = req.read().rows;
        console.log(rows.length);
        UI.items.replace(rows,
            function(row, items) {
                var pdb = new couch.Database("novacut-0-" + row.id.toLowerCase());
                try{
                    var filecount = pdb.view_sync('doc', 'type', {key: 'dmedia/file'}).rows[0].value;
                }
                catch(e){
                    var filecount = 0;
                }
            
                var li = $el('li', {'class': 'project', 'id': row.id});
                var thumb = $el('div', {'class': 'thumbnail'});
                thumb.style.backgroundImage = "url(/_apps/dmedia/novacut-avatar-192.png)";//novacut.att_css_url(row.id);

                var info = $el('div', {'class': 'info'});
                info.appendChild(
                    $el('p', {'textContent': row.key, 'class': 'title'})
                );

                info.appendChild(
                    $el('p', {'textContent': format_date(row.value)})
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
 		    Hub.send('delete_project', row.id)
		    UI.load_items();
		}
		li.appendChild(del);
                thumb.onclick = function() {
                    Hub.send('load_project', row.id)
                }
                info.onclick = function() {
                    Hub.send('load_project', row.id)
                }

                return li;
            }
        );
        UI.items.select(UI.project.id);
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
