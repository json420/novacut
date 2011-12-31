"use strict";

function create_project() {
    var title = $('name').value;
    Hub.send('create_project', title);
}
