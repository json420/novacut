"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db_name);

window.addEventListener('load',
    function() {
        set_title('title', doc.title);
    }
);
