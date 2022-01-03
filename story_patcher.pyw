import sqlite3
import os
import csv
import tkinter as tk

from tkinter import ttk
from shutil import copyfile

import UnityPy

meta_conn = sqlite3.connect('../../meta')
master_conn = sqlite3.connect('../../master/master.mdb')
master_conn.row_factory = sqlite3.Row
m_c = meta_conn.cursor()
mdb_c = master_conn.cursor()

folders = ['translations', 'backup', 'extracted']
for folder in folders:
    try:
        os.mkdir(folder)
    except FileExistsError:
        pass


def extract_storytimeline(dat, meta_path, save_path):
    path = f'../../dat/{dat[:2]}/{dat}'
    backup = f'backup/{dat}'
    if os.path.exists(backup):
        path = backup
    env = UnityPy.load(path)
    data = {}
    for obj in env.objects:
        if obj.type.name == 'MonoBehaviour' and obj.serialized_type.nodes:
            for node in obj.serialized_type.nodes:
                if node.name == 'NextBlock':
                    tree = obj.read_typetree()
                    block = tree['NextBlock'] - 1 * (tree['NextBlock'] > 0)
                    data[block] = {}
                    keep_params = ['Name', 'Text', 'ChoiceDataList']
                    for param in keep_params:
                        data[block][param] = tree[param]
    if data:
        story_data = sorted(data.items())
        story_data.append(story_data.pop(0))
        story_data.pop(0)
        story = [['Language', '日本語'], ['Path', meta_path]]
        for index, line in story_data:
            story.append([])
            story.append(['Line', index])
            story.append(['Name', line['Name']])
            tmp_text = 'Text'
            for sub_line in line['Text'].split('\r\n'):
                story.append([tmp_text, sub_line])
                tmp_text = ''
            for choice_index, choice in enumerate(line['ChoiceDataList']):
                story.append([])
                story.append(['Choice', index])
                story.append(['Number', choice_index + 1])
                tmp_text = 'Text'
                for sub_line in choice['Text'].split('\r\n'):
                    story.append([tmp_text, sub_line])
                    tmp_text = ''
        with open(save_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(story)
            print(f"Extracted {save_path.split('/')[-1]}")


def extract_storyrace(dat, meta_path, save_path):
    path = f'../../dat/{dat[:2]}/{dat}'
    backup = f'backup/{dat}'
    if os.path.exists(backup):
        path = backup
    env = UnityPy.load(path)
    data = {}
    for obj in env.objects:
        if obj.type.name == 'MonoBehaviour' and obj.serialized_type.nodes:
            for node in obj.serialized_type.nodes:
                if node.name == 'textData':
                    tree = obj.read_typetree()
                    for line in tree['textData']:
                        key = line['key']
                        data[key] = {}
                        keep_params = ['text']
                        for param in keep_params:
                            data[key][param] = line[param]
    if data:
        story_data = sorted(data.items())
        story = [['Language', '日本語'], ['Path', meta_path]]
        for index, line in story_data:
            story.append([])
            story.append(['Line', index])
            tmp_text = 'Text'
            for sub_line in line['text'].split('\\n'):
                story.append([tmp_text, sub_line])
                tmp_text = ''
        with open(save_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(story)
            print(f"Extracted {save_path.split('/')[-1]}")


def extract_episode(data):
    dir_paths = [
        'extracted',
        f"extracted/{data['story'].name}",
        f"extracted/{data['story'].name}/{data['chapter'].id}.{data['chapter'].name}"
    ]
    for path in dir_paths:
        try:
            os.mkdir(path)
        except FileExistsError:
            pass

    ep = data['episode']
    if not (ep.multipart and ep.story_type_2):
        str_tl_id = str(ep.tl_id)
        meta_tl_id = '0' * (9 - len(str_tl_id)) + str_tl_id
        if ep.type == 1:
            meta_path, dat = m_c.execute(f"select n,h from a where n LIKE '%storytimeline_{meta_tl_id}'").fetchone()
            extract_storytimeline(dat, meta_path, f"extracted/{data['story'].name}/{data['chapter'].id}.{data['chapter'].name}/{data['episode'].ep_num}.{data['episode'].name}.csv")
        if ep.type == 3:
            meta_path, dat = m_c.execute(f"select n,h from a where n LIKE '%storyrace_{meta_tl_id}'").fetchone()
            extract_storyrace(dat, meta_path, f"extracted/{data['story'].name}/{data['chapter'].id}.{data['chapter'].name}/{data['episode'].ep_num}.{data['episode'].name}.csv")
        return

    for part in range(1, 6):
        part_type = getattr(ep, f'story_type_{part}')
        if part_type in [1, 3]:
            str_tl_id = str(getattr(ep, f'story_id_{part}'))
            meta_tl_id = '0' * (9 - len(str_tl_id)) + str_tl_id
            if part_type == 1:
                meta_path, dat = m_c.execute(f"select n,h from a where n LIKE '%storytimeline_{meta_tl_id}'").fetchone()
                extract_storytimeline(dat, meta_path, f"extracted/{data['story'].name}/{data['chapter'].id}.{data['chapter'].name}/{data['episode'].ep_num}.{data['episode'].name} part{part}.csv")
            if part_type == 3:
                meta_path, dat = m_c.execute(f"select n,h from a where n LIKE '%storyrace_{meta_tl_id}'").fetchone()
                extract_storyrace(dat, meta_path, f"extracted/{data['story'].name}/{data['chapter'].id}.{data['chapter'].name}/{data['episode'].ep_num}.{data['episode'].name} part{part}.csv")


def read_csv_timeline(slot, fp):
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:

            def save(line_data):
                line_index = int(line_data.get('Line', '0'))
                choice_index = int(line_data.get('Choice', '0'))
                story_data.setdefault(line_index, {})
                story_data.setdefault(choice_index, {})
                story_data[choice_index].setdefault('Choices', [])
                if line_index:
                    story_data[line_index] = {**story_data[line_index], **line_data}
                if choice_index:
                    story_data[choice_index]['Choices'].append(line_data)

            reader = csv.reader(f)
            story_data = {}
            line_data = {}
            last_kw = None
            for row in reader:
                data = row[(slot * 2):(slot * 2 + 2)]
                if data != ['', ''] and (data[0] or last_kw):
                    if data[0] != '':
                        last_kw = data[0]
                    if line_data.get(last_kw):
                        try:
                            line_data[last_kw] += f' \r\n{data[1]}'
                        except Exception:
                            pass
                    else:
                        try:
                            data[1] = int(data[1])
                        except ValueError:
                            pass
                        line_data[last_kw] = data[1]
                else:
                    save(line_data)
                    line_data = {}
                    last_kw = None
            save(line_data)
        return story_data
    return {}


def patch_storytimeline(dat, story_data):
    path = f'../../dat/{dat[:2]}/{dat}'
    backup = f'backup/{dat}'
    if not os.path.exists(backup):
        try:
            os.mkdir('backup')
        except FileExistsError:
            pass
        copyfile(path, backup)
    env = UnityPy.load(backup)
    for obj in env.objects:
        if obj.type.name == 'MonoBehaviour' and obj.serialized_type.nodes:
            for node in obj.serialized_type.nodes:
                if node.name == 'NextBlock':
                    tree = obj.read_typetree()
                    block = tree['NextBlock'] - 1 * (tree['NextBlock'] > 0)
                    if story_data.get(block):
                        tree = {**tree, **story_data[block]}
                        for choice in story_data[block].get('Choices', []):
                            try:
                                choice_index = choice.get('Number') - 1
                                tree['ChoiceDataList'][choice_index] = {**tree['ChoiceDataList'][choice_index], **choice}
                            except IndexError:
                                pass
                        if len(story_data[block].get('Text', '')) > 120:
                            tree['Size'] = 2
                        obj.save_typetree(tree)
    with open(path, "wb") as f:
        f.write(env.file.save())


def patch_storyrace(dat, story_data):
    path = f'../../dat/{dat[:2]}/{dat}'
    backup = f'backup/{dat}'
    if not os.path.exists(backup):
        try:
            os.mkdir('backup')
        except FileExistsError:
            pass
        copyfile(path, backup)
    env = UnityPy.load(backup)
    for obj in env.objects:
        if obj.type.name == 'MonoBehaviour' and obj.serialized_type.nodes:
            for node in obj.serialized_type.nodes:
                if node.name == 'textData':
                    tree = obj.read_typetree()
                    for i, line in enumerate(tree['textData']):
                        key = line['key']
                        if story_data.get(key):
                            story_data[key]['text'] = story_data[key]['Text']
                            tree['textData'][i] = {**line, **story_data[key]}
                    obj.save_typetree(tree)
    with open(path, "wb") as f:
        f.write(env.file.save())


def patch_episode(data):
    meta_path, slot, file_path = data
    dat, *_ = m_c.execute(f"select h from a where n LIKE '{meta_path}'").fetchone()
    story_data = read_csv_timeline(slot, file_path)
    if 'storytimeline' in meta_path:
        patch_storytimeline(dat, story_data)
    if 'storyrace' in meta_path:
        patch_storyrace(dat, story_data)


class Story():
    def __init__(self, story_type):
        self.name = story_type.get('name')
        chap_data = mdb_c.execute(f"Select [index], text from text_data where id = {story_type.get('id', '0')}").fetchall()

        ep_list = mdb_c.execute(f"Select * from {story_type.get('table')} {story_type.get('where', '')}").fetchall()
        ep_names = mdb_c.execute(f"Select [index], text from text_data where id = {story_type.get('sub_id', '0')}").fetchall()

        def find_ep(eps, key, val):
            for i, ep in enumerate(eps):
                if ep[key] == val:
                    return eps.pop(i)
            return None

        ep_data = {}
        for id_, name in ep_names:
            ep = find_ep(ep_list, story_type.get('id_key'), id_)
            if ep:
                ep_data[id_] = {**ep, **{'name': name}}

        self.chapters = {id_: Chapter(id_, name) for id_, name in chap_data}

        for id_, data in ep_data.items():
            chap_key = story_type.get('chap_key')
            chap_id = data.get(chap_key)
            if self.chapters.get(chap_id):
                ep = Episode(data)
                self.chapters[chap_id].episodes[ep.tl_id] = ep

    def get_data(self, chap_id, ep_id):
        data = {}
        data['story'] = self
        data['chapter'] = self.chapters[chap_id]
        data['episode'] = data['chapter'].episodes[ep_id]
        return data


class Chapter():
    def __init__(self, id_, name):
        self.id = id_
        self.name = name

        self.episodes = {}


class Episode():
    def __init__(self, data):
        for arg in data:
            setattr(self, arg, data[arg])
            if arg in ['story_number', 'episode_index', 'episode_index_id', 'show_progress_1']:
                self.ep_num = data[arg]
            if arg in ['story_id_1']:
                self.tl_id = data[arg]
                self.multipart = True
            if arg in ['story_id']:
                self.tl_id = data[arg]
                self.multipart = False
                self.type = 1
            if arg in ['story_type_1', 'story_type']:
                self.type = data[arg]


def main():

    root = tk.Tk()
    root.title('Uma Musume Story Patcher')
    root.iconphoto(False, tk.PhotoImage(file='utx_ico_home_umamusume_12.png'))
    root.geometry('900x600')
    root.minsize(600, 400)

    nav = tk.Frame(root)
    nav.pack(side='top', fill='both')

    frame = tk.Frame(root)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    notebook = ttk.Notebook(frame)
    notebook.pack(fill='both', expand=True)

    def treeview_sort_column(tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
        tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))

    trees = []

    def check_status(msg='translated'):
        for dat in os.listdir('backup'):
            path = f'../../dat/{dat[:2]}/{dat}'
            if os.path.exists(path) and os.path.getsize(path) != os.path.getsize(os.path.join('backup', dat)):
                tl_id = int(m_c.execute(f"select n from a where h = '{dat}'").fetchone()[0].split('_')[-1])
                found = False
                for story in stories:
                    for chap_id, chapter in story.chapters.items():
                        if chapter.episodes.get(tl_id):
                            found = set_status(chap_id, tl_id, msg)
                            break
                    if found:
                        break

    def set_status(chap_id, ep_id, msg: str):
        for tree in trees:
            chap = tree.get_children(chap_id)
            if str(ep_id) in chap:
                vals = tree.item(ep_id)['values']
                vals[2] = msg
                tree.item(ep_id, values=vals)
                return True
            break
        return False

    story_types = [
        {'id': 112, 'name': 'Main Story', 'sub_id': 94, 'table': 'main_story_data', 'where': 'where story_number != 0', 'id_key': 'id', 'chap_key': 'part_id'},
        {'id': 189, 'name': 'Event Story', 'sub_id': 191, 'table': 'story_event_story_data', 'id_key': 'id', 'chap_key': 'story_event_id'},
        {'id': 182, 'name': 'Chara Story', 'sub_id': 92, 'table': 'chara_story_data', 'id_key': 'story_id', 'chap_key': 'chara_id'},
        {'id': 182, 'name': 'Training Chara Story', 'sub_id': 181, 'table': 'single_mode_story_data', 'where': 'where card_chara_id != 0', 'id_key': 'story_id', 'chap_key': 'card_chara_id'},
        {'id': 182, 'name': 'Support Chara Story', 'sub_id': 181, 'table': 'single_mode_story_data', 'where': 'where support_chara_id != 0', 'id_key': 'story_id', 'chap_key': 'support_chara_id'},
        {'id': 75, 'name': 'Support Card Story', 'sub_id': 181, 'table': 'single_mode_story_data', 'where': 'where support_card_id != 0', 'id_key': 'story_id', 'chap_key': 'support_card_id'},
    ]
    stories = [Story(story_type) for story_type in story_types]

    for story in stories:

        tab_frame = tk.Frame(notebook)
        tab_frame.pack(fill='both', expand=True)
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)

        notebook.add(tab_frame, text=story.name)

        cols = ('#0', 'Episode', 'Story id', 'Status')
        tree = ttk.Treeview(tab_frame, selectmode='extended', columns=cols[1:])
        for col in cols:
            txt = col
            if col == '#0':
                txt = 'Name'
            tree.heading(col, text=txt, anchor='w', command=lambda _col=col: treeview_sort_column(tree, _col, False))
            tree.column(col, minwidth=0, stretch=False)
        tree.column(cols[0], width=250)
        tree.column(cols[1], width=70)
        tree.column(cols[2], width=100)
        tree.column(cols[3], width=100)

        for chapter in story.chapters.values():
            tree.insert('', tk.END, open=False, iid=chapter.id, text=chapter.name)
            for episode in chapter.episodes.values():
                values = [
                    episode.ep_num,
                    episode.tl_id,
                    ''
                ]
                tree.insert(chapter.id, tk.END, iid=episode.tl_id, text=episode.name, values=(*values,))
        for chapter in tree.get_children():
            if not tree.get_children(chapter):
                tree.delete(chapter)
        tree.grid(row=0, column=0, sticky='NSEW')

        vsb = ttk.Scrollbar(tab_frame, orient="vertical", command=tree.yview)
        vsb.grid(row=0, column=1, rowspan=2, sticky='NSEW')
        tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(tab_frame, orient="horizontal", command=tree.xview)
        hsb.grid(row=1, column=0, sticky='NSEW')
        tree.configure(xscrollcommand=hsb.set)
        trees.append(tree)

    check_status()

    progress = ttk.Progressbar(frame, orient='horizontal', length=100, mode='determinate')
    progress.pack(fill='x')

    def extractStories():
        tree = trees[notebook.index('current')]
        curItems = tree.selection()
        progress['value'] = 0
        frame.update_idletasks()
        length = len(curItems)
        for i, ep_id in enumerate(curItems):
            try:
                if tree.item(ep_id)['values']:
                    chap_id = tree.parent(ep_id)
                    story_index = trees.index(tree)
                    data = stories[story_index].get_data(int(chap_id), int(ep_id))
                    extract_episode(data)
            except Exception as e:
                print(f'Error in extractStories {e}')
            progress['value'] = ((i + 1) / length) * 100
            frame.update_idletasks()

    btn_extract = ttk.Button(nav, text='Extract selected')
    btn_extract.pack(side='left')
    btn_extract.configure(command=extractStories)

    def patchStories():
        progress['value'] = 0
        frame.update_idletasks()
        count = 0
        cur = 0
        for root, subdirs, files in os.walk('translations'):
            count += len(files)
        for root, subdirs, files in os.walk('translations'):
            for file in files:
                cur += 1
                if file.endswith('.csv'):
                    fp = os.path.join(root, file)
                    with open(fp, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        metadata = {}
                        last_kw = None
                        done = {}
                        for row in reader:
                            total_slots = len(row) // 2
                            if len(done) == total_slots:
                                break
                            for slot in range(total_slots):
                                slot_data = row[(slot * 2):(slot * 2 + 2)]
                                if slot_data == ['', '']:
                                    done[slot] = 'True'
                                    continue
                                if done.get(slot):
                                    continue
                                if slot_data[0] != '':
                                    last_kw = slot_data[0]
                                if metadata.get(slot) and metadata[slot].get(last_kw):
                                    metadata[slot][last_kw] = [metadata[slot][last_kw]] + [slot_data[1]]
                                else:
                                    if not metadata.get(slot):
                                        metadata[slot] = {'Slot': slot}
                                    metadata[slot][last_kw] = slot_data[1]
                        for key, settings in metadata.items():
                            lang = settings.get('Language', '')
                            if lang.lower() in ['english', 'en']:
                                try:
                                    patch_episode((settings.get('Path'), settings.get('Slot'), fp))
                                    print(f"Pathched '{file}' in {lang}")
                                except Exception as e:
                                    raise e
                                    print(f'Error in loadStories {e}')

                progress['value'] = ((cur + 1) / count) * 100
                frame.update_idletasks()
        progress['value'] = 100
        frame.update_idletasks()
        check_status()

    btn_load = ttk.Button(nav, text='Patch All')
    btn_load.pack(side='left')
    btn_load.configure(command=patchStories)

    def backup_restore():
        progress['value'] = 0
        frame.update_idletasks()
        dat_list = os.listdir('backup')
        length = len(dat_list)
        check_status('')
        for i, dat in enumerate(dat_list):
            path = f'../../dat/{dat[:2]}/{dat}'
            backup = f'backup/{dat}'
            copyfile(backup, path)
            os.remove(backup)
            print(f'restored {dat}')
            progress['value'] = ((i + 1) / length) * 100
            frame.update_idletasks()

    btn_load = ttk.Button(nav, text='Restore game files')
    btn_load.pack(side='left')
    btn_load.configure(command=backup_restore)

    root.mainloop()


if __name__ == '__main__':
    main()
