"use strict";

var novacut = new couch.Database('novacut-0');
var dmedia = new couch.Database('dmedia-0');

function parse_hash() {
    return window.location.hash.slice(1).split('/');
}

function set_title(id, value) {
    var el = $(id);
    if (value) {
        el.textContent = value;
    }
    else {
        el.textContent = '';
        el.appendChild($el('em', {textContent: 'Untitled'}));
    }
    return el;
}


function project_db(base, ver, project_id) {
    var name = [base, ver, project_id.toLowerCase()].join('-');
    return new couch.Database(name);
}


function novacut_project_db(project_id) {
    return project_db('novacut', 0, project_id);
}


function dmedia_project_db(project_id) {
    return project_db('dmedia', 0, project_id);
}


function create_node(node) {
    return {
        '_id': couch.random_id(),
        'ver': 0,
        'type': 'novacut/node',
        'time': couch.time(),
        'node': node,
    }
}


function create_slice(src, frame_count) {
    var node = {
        'type': 'slice',
        'src': src,
        'start': {'frame': 0},
        'stop': {'frame': frame_count},
        'stream': 'video',
    }
    return create_node(node);
}


function create_sequence() {
    var node = {
        'type': 'sequence',
        'src': [],
    }
    var doc = create_node(node);
    doc.doodle = [];
    return doc;
}


