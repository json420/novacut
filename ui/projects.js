"use strict";

function create_project() {
    var title = UI.title.value;
    Hub.send('create_project', title);
    UI.title.value = '';
}

function open_project(project_id) {
    window.location.assign('cutter.html#' + project_id); 
}

Hub.connect('project_created', open_project);


var UI = {
    on_projects: function(req) {
        var rows = req.read()['rows'];
        var div = $('projects');
        div.textContent = '';
        rows.forEach(function(row) {
            var _id = row.id;
            var p = $el('p', {'id': _id, 'class': 'project'});
            set_title(p, row.value);
            p.onclick = function() {
                open_project(_id);
            }
            div.appendChild(p);
        });
    },
}


window.addEventListener('load',
    function() {
        UI.title = $('title');
        novacut.view(UI.on_projects, 'project', 'atime', {descending: true});
    }
);
