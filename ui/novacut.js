"use strict";

var novacut = new couch.Database('novacut-0');

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

