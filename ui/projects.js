"use strict";


function open_project(project_id) {
    window.location.assign('cutter.html#' + project_id); 
}

Hub.connect('project_created', open_project);


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
    },

    on_items: function(req) {
        var rows = req.read().rows;
        console.log(rows.length);
        UI.items.replace(rows,
            function(row, items) {
                var li = $el('li', {'class': 'project', 'id': row.id});

                var thumb = $el('div', {'class': 'thumbnail'});
                thumb.style.backgroundImage = novacut.att_css_url(row.id);

                var info = $el('div', {'class': 'info'});
                info.appendChild(
                    $el('p', {'textContent': row.key, 'class': 'title'})
                );

                info.appendChild(
                    $el('p', {'textContent': format_date(row.value)})
                );

                info.appendChild(
                    $el('p', {'textContent': '38 files, 971 MB'})
                );

                li.appendChild(thumb);
                li.appendChild(info);

                li.onclick = function() {
                    open_project(row.id);
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
