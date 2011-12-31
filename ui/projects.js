"use strict";

function create_project() {
    var title = $('title').value;
    Hub.send('create_project', title);
    $('title').value = '';
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
            if (row.value) {
                p.textContent = row.value;
            }
            else {
                p.appendChild($el('em', {textContent: 'Untitled'}));
            }
            p.onclick = function() {
                open_project(_id);
            }
            div.appendChild(p);
        });
    },
}


window.addEventListener('load',
    function() {
        novacut.view(UI.on_projects, 'project', 'atime', {descending: true});
    }
);
