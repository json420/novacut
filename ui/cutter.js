"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db);

window.addEventListener('load',
    function() {
        $('title').textContent = doc['title'];
    }
);
