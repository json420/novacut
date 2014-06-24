# novacut: the distributed video editor
# Copyright (C) 2011 Novacut Inc
#
# This file is part of `novacut`.
#
# `novacut` is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# `novacut` is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
# more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with `novacut`.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   David Jordan <djordan2@novacut.com>

"""
Build Blender VSE sequence from a Novacut edit.

Copy this file into a text file in Blender's script editor, edit the lines at the bottom of this script and execute with "Run Script"
"""

import bpy
import optparse

from microfiber import Server
from dmedia.service import init_if_needed, get_env, get_proxy

import novacut
from novacut import schema, migration, views

env = get_env()

Dmedia = get_proxy()

server = Server(env)
dmedia_main_db = server.database('dmedia-1')
novacut_main_db = server.database('novacut-1')

'''
data is tracked by object name since blender vse strips can't store custom properties
ID: video slice for the slice in the Novacut edit with ID
a_ID: video slice for the slice in the Novacut edit with ID
'''

class vse_novacut_proj:
    def __init__(self, proj_id, seq_start_frame=0, first_scene=True, last_scene=True):
        self.proj_id  = proj_id
        self.seq_start_frame = seq_start_frame
        self.proj_db = server.database(self.proj_id)
        self.set_vse_seq_start = first_scene
        self.set_vse_seq_end = last_scene
    
    def add_slice(self, proj_db, slice_id, playhead):
        slice_doc = proj_db.get(slice_id)
        (id, status, path) = Dmedia.Resolve(slice_doc['node']['src'])
        
        slice_src_id = slice_doc['node']['src']
        slice_start_frame = slice_doc['node']['start']
        slice_stop_frame = slice_doc['node']['stop']
        
        data = bpy.data.movieclips.load(filepath=path)
        data.name = slice_id
        newstrip = bpy.ops.sequencer.movieclip_strip_add(\
            channel=1, frame_start=playhead - slice_start_frame,
            replace_sel=True, overlap=False, clip=data.name)
        cur_slice_strip = bpy.context.scene.sequence_editor.sequences_all[slice_id]
        
        cur_slice_strip.frame_offset_start = slice_start_frame
        cur_slice_strip.frame_offset_end = cur_slice_strip.frame_duration - slice_stop_frame - 1
        cur_slice_strip.channel = 1
        
        a_newstrip = bpy.ops.sequencer.sound_strip_add(\
            channel=0, frame_start=playhead - slice_start_frame,
            replace_sel=True, overlap=False, filepath=path)
        a_cur_slice_strip = bpy.context.scene.sequence_editor.active_strip
        a_cur_slice_strip.name = 'a_' + slice_id
        
        a_cur_slice_strip.frame_offset_start = slice_start_frame
        a_cur_slice_strip.frame_offset_end = a_cur_slice_strip.frame_duration - slice_stop_frame - 1
        a_cur_slice_strip.channel = 0
        
        duration = slice_stop_frame - slice_start_frame + 1
        playhead = playhead + duration
        
        print(newstrip)
        print('start: ' + str(slice_doc['node']['start']) + ' end: ' + str(slice_doc['node']['stop']))
        print(' ')
        return playhead

    def add_sequence(self, proj_db, seq_id, playhead):
        seq_doc = proj_db.get(seq_id)
        slice_ids = seq_doc['node']['src']
        for slice_id in slice_ids:
            playhead = self.add_slice(proj_db, slice_id, playhead)
        return playhead

    def add_root(self, proj_db, root_id):
        playhead = self.seq_start_frame
        if self.set_vse_seq_start:
            bpy.context.scene.frame_start = playhead
            
        playhead = self.add_sequence(proj_db, root_id, playhead)
        
        if self.set_vse_seq_end:
            bpy.context.scene.frame_end = playhead - 1


    def import_proj(self):
        res = self.proj_db.view('doc', 'type')['rows']
        playhead = self.seq_start_frame
        for doc in res:
            if doc['key'] == 'novacut/project':
                proj_doc = self.proj_db.get(doc['id'])
                root_id = proj_doc['root_id']
                print(root_id)
                self.add_root(self.proj_db, root_id)        
                
def show_novacut_projects():
    for name in server.get('_all_dbs'):
        if name.startswith('novacut-1-'):
            proj_db = server.database(name)
            res = proj_db.view('doc', 'type')['rows']
            for doc in res:
                if doc['key'] == 'novacut/project':
                    proj_doc = proj_db.get(doc['id'])
                    print(proj_doc['title'] + ":")
                    print(name)
                    
#1) Get list of Novacut projects by title and database name
#show_novacut_projects()

#2) import project with given database name 
#proj_a = vse_novacut_proj('novacut-1-some-id-here', 0)
proj_a.import_proj()

