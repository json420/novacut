"use strict";

var novacut = new couch.Database('novacut-0');

function parse_hash() {
    return window.location.hash.slice(1).split('/');
}

