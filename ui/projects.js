"use strict";

function create_project() {
    var title = $('title').value;
    Hub.send('create_project', title);
}

function open_project(project_id) {
    window.location.assign('cutter.html#' + project_id); 
}

Hub.connect('project_created', open_project);
