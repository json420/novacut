"use strict";

function create_project() {
    var title = $('title').value;
    Hub.send('create_project', title);
}

Hub.connect('project_created',
    function(project_id) {
        console.log(project_id);
        window.location.assign('cutter.html#' + project_id); 
    }
)
