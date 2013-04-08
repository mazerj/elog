#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; py-indent-offset: 4; -*-

# elog database has 4 tables:
#   - SESSION: main daily record (one per day)
#     * EXPER: one per experiment or recording site (many per SESSION)
#       + UNIT: one per isolated unit (many per EXPER)
#       + DFILE: one per datafile/run (many per EXPER)

import string, sys, os, datetime, time, re

from keyboard import keyboard

if os.environ.has_key('DISPLAY'):
    from Tkinter import *
    from tkMessageBox import askyesno
    import Pmw_1_3_2 as Pmw
    import tkdialogs

from tools import *
import dumphtml
import layout
import initdb

def attach(tk, db, im=None, title='no title', note='',
           srctable=None, srcID=None):
    """Use imagemagick 'import' command to grab a screen capture
    of a window or region as JPEG image and store in string
    """

    if im is None:
        im = os.popen('import jpeg:-', 'r').read().encode('base64')

    if db.query("""INSERT INTO attachment"""
                """ (type,user,date,title,note,srctable,srcID,data)"""
                """ VALUES ('%s','%s','%s','%s','%s','%s',%d,'%s')""" % \
                ('jpeg', getuser(), today(), title, note,
                 srctable, srcID, im,)) is None:
        sys.stderr.write("db insert attachment error\n")
        return
    rows = db.query("""SELECT attachmentID FROM attachment"""
                    """ ORDER BY attachmentID DESC LIMIT 1""")
    id = rows[0]['attachmentID']
    if tk:
        w = AttachmentViewer(tk, db, id, title=title)
    return id


class AttachmentViewer(Toplevel):
    attachmentList = {}

    def __init__(self, master, db, id, title=None, note=None, **kw):
        self.db = db
        self.id = id

        self.im, self.rows = self.getattach()
        if title:
            self.rows['title'] = title
        if note:
            self.rows['note'] = note

        Toplevel.__init__(self, master, **kw)
        self.winfo_toplevel().title('Attachment#%d' % self.id)

        f = Frame(self)
        f.pack(expand=1, fill=BOTH)

        bb = Frame(f)
        bb.pack(expand=1, fill=X)

        Button(bb, text='save', \
               command=self.save).pack(side=LEFT, expand=0)
        Button(bb, text='delete', \
               command=self.db_delete).pack(side=LEFT, expand=0)

        self.rv = RecordView(f, layout.ATTACHMENT_FIELDS, self.db)
        self.rv.pack(side=TOP, expand=1, fill=BOTH)
        self.rv.setall(self.rows)

        Label(f, image=self.im, \
              relief=SUNKEN, borderwidth=3).pack(side=BOTTOM, padx=10, pady=10)

        self.protocol("WM_DELETE_WINDOW", self.close)

        AttachmentViewer.attachmentList[self.rows['attachmentID']] = self

    def getattach(self):
        import PIL.Image, StringIO, ImageTk

        rows = self.db.query("""SELECT * FROM attachment"""
                             """ WHERE attachmentID=%d""" % (self.id,))
        imstr = rows[0]['data'].decode('base64')
        im = ImageTk.PhotoImage(PIL.Image.open(StringIO.StringIO(imstr)))
        return im, rows[0]

    def db_delete(self):
        if self.db.readonly:
            warn(self, "\nRead only mode!\n", ("Ok",))
            return

        i = warn(self, "\nReally delete attachment?\n",
                 ("Ok", "Cancel"))
        if not i == 'Ok':
            return

        # delete actual attachment
        self.db.query("""DELETE FROM attachment WHERE attachmentID=%d""" %
                      (self.id,))

        # file dfile's that link to it and delete links
        rows = self.db.query("""SELECT dfileID,attachlist FROM dfile"""
                             """ WHERE attachlist LIKE '%%%d,%%'""" %
                             (self.id,))
        for row in rows:
            try:
                al = row['attachlist'].split(',')
                al.remove(str(self.id))
                al = string.join(al, ',')
                self.db.query("""UPDATE dfile SET attachlist='%s'"""
                              """ WHERE dfileID=%d""" % (al, row['dfileID']))
            except ValueError:
                pass

        self.destroy()

    def save(self):
        self.rv.save(self.db, table='attachment',
                     key=('AttachmentID', self.id))

    def close(self):
        self.save()
        self.destroy()
        del AttachmentViewer.attachmentList[self.rows['attachmentID']]


def clipcopy(widget, str):
    """Copy string to clipboard for standard pasting
    """
    widget.clipboard_clear()
    widget.clipboard_append(str)

# left-right hack from:
#  http://mail.python.org/pipermail/tkinter-discuss/2011-January/002752.html
class Checkbutton2(Frame):
    def __init__(self, master=None, **kw):

        if kw.has_key('text'):
            text = kw['text']
            del(kw['text'])
        else:
            text = ''

        if kw.has_key('state'):
            state = kw['state']
            del(kw['state'])
        else:
            state = None

        Frame.__init__(self, master, **kw)

        self.var = IntVar()
        self.label = Label(self, text=text)
        self.label.pack(side=LEFT, fill=X)
        self.checkbutton = Checkbutton(self, variable=self.var)
        if not state is None:
            self.checkbutton.configure(state=state)
        self.checkbutton.pack(side=RIGHT)

    def setvalue(self, value):
        if value == '':
            value = 0
        self.var.set(value)

    def getvalue(self):
        v = self.var.get()
        return v

class RecordView(Frame):
    def __init__(self, master, fields, db, **kwargs):
        Frame.__init__(self, master, **kwargs)

        self._entries = {}
        self._validators = {}
        self._converters = {}
        self._children = []
        self._children_info = {}
        self.db = db

        self.frame1 = Frame(self)
        self.frame1.pack(expand=0, fill=X, side=TOP)
        self.frame2 = Frame(self)
        self.frame2.pack(expand=1, fill=BOTH, side=BOTTOM)

        elist = []
        elist_by_col = {}
        for fd in fields:
            (fieldname, validator, converter, state, sz, pos) = fd
            (row, col, cspan) = pos
            if not elist_by_col.has_key(col):
                elist_by_col[col] = []

            if validator == TEXT:
                (w, h) = sz
                e = Pmw.ScrolledText(self.frame2,
                                     borderframe=1,
                                     text_height=h, text_width=w,
                                     labelpos='w', label_text=fieldname)
                e.pack(expand=1, fill=BOTH)
                e.component('text').bind('<Alt-t>', ins_time)
                e.component('text').configure(wrap=WORD)
                if not GuiWindow.showlinks.get():
                    e.component('text').tag_config('experlink', elide=1)
                else:
                    e.component('text').tag_config('experlink', foreground='red')
                e.component('text')['state'] = state
            elif validator == BOOL:
                e = Checkbutton2(self.frame1, text=fieldname, state=state)
                e.grid(row=row, column=col, columnspan=cspan, sticky=W)
            else:
                e = Pmw.EntryField(self.frame1, labelpos='w',
                                   label_text=fieldname, validate=validator)
                if sz: e.component('entry')['width'] = sz
                e.grid(row=row, column=col, columnspan=cspan, sticky=E+W)
                e.component('entry')['state'] = state

            elist.append(e)
            elist_by_col[col].append(e)

            self._entries[fieldname] = e
            self._validators[fieldname] = validator
            self._converters[fieldname] = converter

        for col in elist_by_col.keys():
            Pmw.alignlabels(elist_by_col[col])

    def keys(self):
        """Get a list of keys (aka fields) for this record.
        """
        return self._entries.keys()

    def setval(self, name, value):
        """Set value of specified field in worksheet.
        """
        if self._converters[name] == sdate:
            self._entries[name].setvalue(sdate(value))
        else:
            self._entries[name].setvalue("%s" % value)
            if self._validators[name] == TEXT:
                txt = self._entries[name].component('text')
                begin = '0.0'
                while 1:
                    # iterate over all intact exper hyperlinks and insert a
                    # an exper widget
                    begin = txt.search('<elog:exper=.*>',
                                     begin, stopindex=END, regexp=1)
                    if not begin:
                        break
                    end = txt.search('>', begin, stopindex=END)
                    if end:
                        end = end+'+1c'
                        txt.tag_add('experlink', begin, end)

                        (date, exper) = unlink_exper(txt.get(begin, end))

                        ew = ExperWindow(txt, self.db, name='%s' % exper,
                                         relief=RIDGE, borderwidth=2)
                        ew.fill(exper=exper, date=date)
                        txt.window_create(end, window=ew, padx=10)
                        self._children.append(ew)
                        self._children_info[ew] = 'exper:%s' % exper
                        begin = end
                txt.see(END)

    def setall(self, dict):
        """Set all values for the worksheet based on values in the dictionary.
        """
        for name in dict.keys():
            if self._entries.has_key(name):
                self._entries[name].setvalue("%s" % dict[name])

    def getval(self, name):
        """Get current on-screen value of indicated field.
        """
        v = self._entries[name].getvalue()
        if self._validators[name] == TEXT:
            v = v[:-1]
        c = self._converters[name]
        if c:
            try:
                return c(v)
            except ValueError:
                return None
        else:
            return v

    def getall(self):
        """Get dictionary of all fields with current on-screen values.
        """
        d = {}
        for k in self.keys():
            d[k] = self.getval(k)
        return d

    def save(self, db, table, key=(None,None)):
        """Save current on-screen record to specified database table.
        """
        if db.readonly:
            return

        (keyfield, keyvalue) = key

        names = []
        values = []
        keys = self.keys()
        for k in keys:
            v = self.getval(k)
            if v is not None:
                if type(v) is types.UnicodeType:
                    v = str(v)
                values.append(v)
                names.append(k)
        if keyvalue:
            if not keyfield in keys:
                names.append(keyfield)
                values.append(keyvalue)
            l = ''
            for k in keys:
                if not self.getval(k) is None:
                    v = "'" + str(self.getval(k)).replace("'", "\\'") + "'"
                    if len(l):
                        l = l + ','
                    l = l + "%s=%s" % (k, v)
            db.query("""UPDATE %s SET %s WHERE %s='%s'""" % \
                     (table, l, keyfield, keyvalue))
        else:
            db.query("""INSERT INTO %s (%s) VALUES %s""" % \
                     (table, string.join(names, ','), tuple(values)))

        for child in self._children:
            try:
                child.save()
            except:
                # this doesn't seem to matter -- it sometimes happens
                # when trying to save the child exper worksheets, but
                # they seem to get saved anyway -- still can't figure
                # out why..
                Msg('save err: %s' % self._children_info[child])

        Msg("Saved record.")

class DatafileFrame(Frame):
     def __init__(self, master, db, src, **kwargs):
        Frame.__init__(self, master, **kwargs)

        self.db = db

        rows = self.db.query("""SELECT * FROM dfile WHERE src='%s'""" %
                             (src,))

        tag = '%s/%s' % (rows[0]['date'], os.path.basename(src))
        link = "<elog:dfile=%s>" % (tag,)

        f = Frame(self)
        f.pack(expand=1, fill=X)

        self.rv = RecordView(self, layout.DFILE_FIELDS, db)
        self.rv.pack(expand=1, fill=BOTH)
        self.rv.setall(rows[0])
        self.dfileID = rows[0]['dfileID']

        b = Button(f, text=os.path.basename(src), \
                   command=lambda w=master,l=link: clipcopy(w,l))
        createToolTip(b, 'copy elog link')
        b.pack(side=LEFT)

        b = Button(f, text='fullpath', \
                   command=lambda w=master,l=link: clipcopy(w,"'%s'"%src))
        createToolTip(b, "copy ''%s''" % src)
        b.pack(side=LEFT)

        b = Button(f, text='attach',
                   command=lambda s=self,t=tag:s.add_attachment(t))
        createToolTip(b, 'screen grab window as attachment')
        b.pack(side=LEFT)

        if len(self.find_attachments()) > 0:
            b = Button(f, text='open attachments', \
                       command=self.open_attachments)
            createToolTip(b, 'open all attachments')
            b.pack(side=LEFT)


     def save(self):
         self.rv.save(self.db, table='dfile',
                      key=('dfileID', self.dfileID))

     def add_attachment(self, tag):
         attid = attach(self, self.db, im=None, title=tag,
                        srctable='dfile', srcID=self.dfileID)

         rows = self.db.query("""SELECT attachlist FROM dfile"""
                              """ WHERE dfileID=%d""" %
                              (self.dfileID,))
         new = rows[0]['attachlist'] + '%d,' % attid
         self.db.query("""UPDATE dfile SET attachlist='%s'"""
                       """ WHERE dfileID=%d""" %
                       (new, self.dfileID))

     def find_attachments(self):
         rows = self.db.query("""SELECT attachlist FROM dfile"""
                              """ WHERE dfileID=%d""" %
                              (self.dfileID,))
         alist = []
         for a in rows[0]['attachlist'].split(','):
             if len(a): alist.append(a)
         return alist


     def open_attachments(self):
         alist = [int(x) for x in self.find_attachments()]
         if len(alist) > 0:
             for aid in alist:
                 if AttachmentViewer.attachmentList.has_key(aid):
                     # window already open, recycle it
                     try:
                         AttachmentViewer.attachmentList[aid].lift()
                     except:
                         # rare error, when opening before delete finishes..
                         del AttachmentViewer.attachmentList[aid]
                         AttachmentViewer(self, self.db, aid)
                 else:
                     AttachmentViewer(self, self.db, aid)
         else:
             warn(self, 'No attachments', ("Ok",))

class UnitWindow:
    def __init__(self, db, exper, unit):
        self.db = db
        self.exper = exper
        self.unit = unit

        page = self.exper.getunitbook().add(unit)
        b = Button(page, text='Delete %s' % unit,
                   command=self.delete)
        b.pack(side=TOP, anchor=W)
        createToolTip(b, 'delete unit from database forever!')

        self.rv = RecordView(page, layout.UNIT_FIELDS, db)
        self.rv.pack(side=TOP, expand=1, fill=BOTH)

        d = self.exper.rv.getall()

        rows = self.db.query("""SELECT * FROM unit"""
                             """ WHERE animal='%s' AND date='%s' AND"""
                             """ exper='%s' AND unit='%s'""" %
                             (d['animal'], d['date'], d['exper'], unit))
        if len(rows):
            self.rv.setall(rows[0])
        else:
            # new unit, seed the forms

            # Start by inheriting form values from the last day in
            # the database for this animal. However, for some slots
            # this is bad thing (ncorrect etc), so the values are
            # overridden below to resonable starting values

            rows = self.db.query("""SELECT * FROM unit"""
                                 """ WHERE animal='%s'"""
                                 """ ORDER BY date DESC LIMIT 1""" %
                                 (d['animal'],))
            if len(rows):
                well = rows[0]['well']
            else:
                well = 0

            # override values that shouldn't be inherited from last day:

            self.rv.setall(dict={
                'unit':self.unit,
                'exper':d['exper'],
                'animal':d['animal'],
                'date':d['date'],
                'well':well,
                'crap':0,
                })
        self.rv.pack(side=TOP)

        # this resizes the NoteBook widget to fit the unit view
        self.exper.getunitbook().setnaturalsize()

    def delete(self):
        """Delete this unit from SQL database and delete from GUI.
        """

        if self.db.readonly:
            warn(self, "\nRead only mode!\n", ("Ok",))
            return

        i = warn(self.exper,
                 "\nReally delete %s?\n" % self.unit,
                 ("Ok", "Cancel"))
        if i == 'Ok':
            self.save()
            d = self.rv.getall()
            self.exper.unitbook.delete(self.unit)
            self.exper.unitlist.remove(self)
            if len(self.exper.unitlist) == 0:
                self.exper.unitbook.destroy()
                self.exper.unitbook = None

            # delete from database -- don't do this the other way around..
            self.db.query("""DELETE FROM unit"""
                          """ WHERE animal='%s' AND date='%s' AND"""
                          """ exper='%s' AND unit='%s'""" %
                          (d['animal'], d['date'], d['exper'], self.unit,))

    def save(self):
        """Save unit data to SQL database
        """
        d = self.rv.getall()
        rows = self.db.query("""SELECT * FROM unit"""
                             """ WHERE animal='%s' AND date='%s' AND"""
                             """ exper='%s' AND unit='%s'""" %
                             (d['animal'], d['date'], d['exper'], d['unit'],))
        if len(rows) == 0:
            self.rv.save(self.db, table='unit')
        else:
            self.rv.save(self.db, table='unit',
                         key=('unitID', rows[0]['unitID']))

class ExperWindow(Frame):
    def __init__(self, master, db, name=None, **kwargs):
        Frame.__init__(self, master, **kwargs)

        self.db = db
        self.date = None
        self.exper = None

        buttonbar = Frame(self)
        buttonbar.grid(row=0, column=0, sticky=E+W)

        if name:
            Label(buttonbar, text=name).pack(side=LEFT)
        b = Button(buttonbar, text='New Unit', \
                   command=self.new_unit)
        createToolTip(b, 'create new unit (TTL etc)')
        b.pack(side=LEFT)

        self.rv = RecordView(self, layout.EXPER_FIELDS, db)
        self.rv.grid(row=1, column=0, sticky=E+W)

        self.unitbook = None
        self.unitlist = []

    def getunitbook(self):
        """Get handle for unit-notebook, or else make one if it doesn't exist.
        """
        if not self.unitbook:
            self.unitbook = Pmw.NoteBook(self)
            self.unitbook.grid(row=2, column=0, sticky=E+W)
            self.unitbook['raisecommand'] = lambda tab,n=self.unitbook: \
                                            raisetab(tab, n)
        return self.unitbook

    def fill(self, dict=None, exper=None, date=None):
        if dict:
            self.rv.setall(dict)
            self.date = dict['date']
            self.exper = dict['exper']
        elif exper and date:
            rows = self.db.query("""SELECT * FROM exper"""
                                 """ WHERE exper='%s' AND date='%s'""" %
                                 (exper, date,))
            if len(rows) > 0:
                self.rv.setall(rows[0])
                self.date = date
                self.exper = exper

                rows = self.db.query("""SELECT * FROM unit"""
                                     """ WHERE animal='%s' AND date='%s'"""
                                     """ AND exper='%s'""" %
                                     (rows[0]['animal'],
                                      rows[0]['date'], rows[0]['exper'],))
                for row in rows:
                    u = UnitWindow(self.db, self, row['unit'])
                    self.unitlist.append(u)
        d = self.rv.getall()

        # get list of datafiles
        rows = self.db.query("""SELECT src FROM dfile"""
                             """ WHERE exper='%s' AND date='%s'"""
                             """ ORDER BY dfileID""" % (exper, date,))
        nr = 3
        self.dfiles = []
        for row in rows:
            w = DatafileFrame(self, self.db, row['src'], \
                              borderwidth=2, relief=RIDGE)
            w.grid(row=nr, column=0, sticky=E+W)
            self.dfiles.append(w)
            nr = nr + 1

    def save(self):
        """
        Save exper to SQL database
        """
        d = self.rv.getall()

        # first save all units
        for u in self.unitlist[:]:
            u.save()

        # next save all dfiles
        for df in self.dfiles:
            df.save()

        # then save exper
        rows = self.db.query("""SELECT experID,exper,date FROM exper"""
                             """ WHERE exper='%s' and date='%s'""" %
                             (d['exper'], d['date'],))
        if len(rows) > 1:
            for n in range(len(rows)):
                print rows[n]
            warn(self, 'corruption: duplicate exper!')
        else:
            if len(rows) > 0:
                self.rv.save(self.db, table='exper',
                            key=('experID', rows[0]['experID']))
            else:
                self.rv.save(self.db, table='exper',
                             key=('experID', None))

    def new_unit(self, unit=None):
        d = self.rv.getall()
        if unit is None:
            unit = ask(self, 'new unit', 'TTL')
            if unit is None:
                return

        rows = self.db.query("""SELECT unitID FROM unit"""
                             """ WHERE animal='%s' AND date='%s' AND"""
                             """ exper='%s' AND unit='%s'""" %
                             (d['animal'], d['date'], d['exper'], unit,))
        if len(rows) > 0 or unit in self.getunitbook().pagenames():
            warn(self, 'no joy: %s already exists' % unit)
            return 0
        else:
            self.unitlist.append(UnitWindow(self.db, self, unit))
            self.getunitbook().selectpage(unit)

class SessionWindow(Frame):
    def __init__(self, master, db, animal, **kwargs):
        Frame.__init__(self, master, **kwargs)

        self.db = db
        self.animal = animal
        self.n = 0

        f = Frame(self)
        self.datew = Label(f, text="", fg='blue', anchor=W)
        self.datew.pack(side=LEFT, fill=X, expand=1)

        self.status = Label(f, text="", fg='red', anchor=E)
        self.status.pack(side=LEFT, fill=X, expand=1)

        f.pack(side=TOP, fill=X, expand=0, pady=2)

        Msg(window=self.status)

        self.rv = RecordView(self, layout.SESSION_FIELDS, db)
        self.rv.pack(side=BOTTOM, fill=BOTH, expand=1)

    def view(self, date=None):
        rows = self.db.query("""SELECT sessionID, date FROM session"""
                             """ WHERE animal='%s' ORDER BY date""" %
                             (self.animal,))

        if len(rows) == 0:
            return 0

        if date:
            n = None
            for i in range(len(rows)):
                if ("%s" % rows[i]['date']) == date:
                    n = i
                    break
            if n is None:
                return 0
            self.n = n

        nmax = len(rows) - 1

        self.n = max(0, min(self.n, nmax))
        rows = self.db.query("""SELECT * FROM session"""
                             """ WHERE sessionID=%d ORDER BY date""" %
                             (rows[self.n]['sessionID'],))
        row = rows[0]
        for k in self.rv.keys():
            self.rv.setval(k, row[k])
        s = '%d/%d recs' % (1+self.n, len(rows),)

        d = self.rv.getall()
        rows = self.db.query("""SELECT exper FROM exper"""
                             """ WHERE animal='%s' and date='%s'"""
                             """ ORDER BY exper ASC""" %
                             (d['animal'], d['date'],))

        dstr = time.strftime('%a %Y-%m-%d',
                             time.strptime(d['date'], '%Y-%m-%d'))
        self.datew.configure(text='%s :: %s     [%s@%s]' % \
                             (d['animal'], dstr, self.db.db, self.db.host))

        # cache pointer to last record accessed in homedir for next time
        cachestate(d['animal'], d['date'])

        if self.check() > 0:
            Msg('inserted missing exper; refresh window!')

        return 1

    def save(self):
        d = self.rv.getall()

        animal = self.rv.getval('animal')
        date = self.rv.getval('date')
        if len(animal) == 0:
            warn(self, "Please specify animal to save.")
            return 0
        if len(date) == 0:
            warn(self, "Please specify date to save.")
            return 0

        rows = self.db.query("""SELECT sessionID FROM session"""
                             """ WHERE animal='%s' and date='%s'""" %
                             (d['animal'], d['date'],))
        n = len(rows)

        if n > 1:
            # this is bad, should never happen
            warn(self, 'Duplicated sessionId!')
        elif n == 1:
            # update existing session
            sessionID = rows[0]['sessionID']
            e = self.rv.save(self.db, table='session',
                             key=('sessionID', sessionID))
        else:
            # create entry for a brand new session
            e = self.rv.save(self.db, table='session')

        Msg("Saved session.")

        return 1

    def today(self, date=None):
        """
        Create a new log entry -- default is for TODAY, otherwise for
        the specified date (in the past!)
        """

        animal = self.animal
        if date:
            today = date
        else:
            today = datetime.date(1,1,1).today()

        rows = self.db.query("""SELECT * FROM session"""
                             """ WHERE animal like '%s' and date='%s'""" %
                             (animal, today,))
        if len(rows) > 1:
            warn(self,
                 'Multiple matching records for today.\nTry picking an animal.')
            return
        elif len(rows) == 1:
            # exactly one matching entry, just edit it..
            row = rows[0]
            for k in self.rv.keys():
                self.rv.setval(k, row[k])
        else:
            # this is a new entry...

            #
            # BELOW ARE THE DEFAULT FIELD SETTINGS FOR A NEW ENTRY
            #
            # fill in best guesses and start editing
            if animal == '%':
                # leave animal blank, save will enforce this..
                self.rv.setval("animal", "")
            else:
                self.rv.setval("animal", animal)

            self.rv.setval("user", getuser())
            self.rv.setval("computer", gethost())
            self.rv.setval("date", today)
            self.rv.setval("restricted", "1")
            self.rv.setval("tested", "1")
            self.rv.setval("water_work", "")
            self.rv.setval("water_sup", "")
            self.rv.setval("fruit", "")
            self.rv.setval("weight", "")
            self.rv.setval("note", "")
            self.rv.setval("ncorrect", "0")
            self.rv.setval("ntrials", "0")

        self.n = 1e6

    def textview(self):
        d = self.rv.getall()
        rows = self.db.query("""SELECT * FROM session """
                             """ WHERE animal='%s' AND date='%s'""" %
                             (d['animal'], d['date'],))
        if len(rows) == 0:
            warn(self, 'nothing to see!')
        else:
            textwarn('db view', rep_note(self.db, rows[0]))

    def find(self):
        s = ask(self, 'find (YYYY-MM-DD)', '')
        if s:
            ss = string.split(s, '-')
            if len(ss) == 3:
                if not self.view(date=s):
                    warn(self, "Can't find date: '%s'" % s)
            else:
                    warn(self, "Invalid date: '%s'" % s)

    def check(self):
        """Check database to see if entry for specified date is
        missing exper-hyperlinks (inaccessible expers..)
        """
        d = self.rv.getall()
        animal = d['animal']
        date = d['date']

        missing = 0
        # find all exper's that don't have a hyperlink in a note field
        rows = self.db.query("""SELECT exper,date FROM exper"""
                             """ WHERE animal='%s' and date='%s'""" %
                             (animal, date,))
        for row in rows:
            if int(row['exper'][-4:]) > 0:
                link = "<elog:exper=%s/%s>" % (row['date'], row['exper'])
                if string.find(d['note'], link) < 0:
                    sys.stderr.write('missing link: %s' % link)
                    missing = missing + 1
                    d['note'] = d['note'] + '\n' + link + '\n'

        if missing > 0:
            self.rv.setall(d)

        return missing

class GuiWindow(Frame):
    def __init__(self, master, db, animal='%', **kwargs):
        self.animal = animal
        self.db = db

        Frame.__init__(self, master, **kwargs)

        menu = Pmw.MenuBar(self, hull_relief=RAISED, hull_borderwidth=1)

        menu.addmenu('File', '', '')
        menu.addmenu('Edit', '', '')
        menu.addmenu('Animals', '', '')
        menu.addmenuitem('File', 'command', label='Save (Ctrl-S)',
                         command=self.save)
        menu.addmenuitem('File', 'command', label='Exit w/out save',
                         command=lambda tk=master: die(tk))
        menu.addmenuitem('File', 'command', label='Quit (save first)',
                         command=self.quit)

        menu.addmenuitem('Edit', 'command', label='Text View',
                         command=lambda s=self: s.session.textview())
        menu.addmenuitem('Edit', 'command', label='Find exper/date (Alt-G)',
                         command=lambda s=self: s.session.find())
        menu.addmenuitem('Edit', 'separator')
        GuiWindow.showlinks = IntVar()
        GuiWindow.showlinks.set(0)

        menu.addmenuitem('Edit', 'checkbutton', label='show links',
                         variable=GuiWindow.showlinks,
                         command=lambda s=self:s.jump(0))

        for a in find_animals(db):
            menu.addmenuitem('Animals', 'command', label=a,
                             command=lambda s=self,a=a,tk=master: \
                             s.selanimal(tk,a))

        menu.pack(side=TOP, expand=0, fill=X)

        menuhull = Frame(menu.component('hull'))
        menuhull.pack(side=RIGHT)

        if db.readonly:
            Label(menuhull, text='READ-ONLY',
                  fg='red', padx=10).pack(side=LEFT, expand=0)

        b = Button(menuhull, text='Refresh',
                   command=lambda s=self: s.jump(0))
        createToolTip(b, 'refresh gui window (Alt-R)')
        b.pack(side=LEFT)

        b = Button(menuhull, text='New Exper',
                   command=lambda s=self: s.new_exper())
        createToolTip(b, 'create new numbered exper/rec-site in database (Alt-N)')
        b.pack(side=LEFT)

        createToolTip(b, 'go to today')
        b.pack(side=LEFT, expand=0)
        b = Button(menuhull, text='Today',
                   command=lambda s=self: s.session.today())
        createToolTip(b, 'go to today')
        b.pack(side=LEFT, expand=0)

        b = Button(menuhull, text='|<',
                   command=lambda s=self: s.jump(-1e6))
        createToolTip(b, 'first record (Alt-Ctl-Home)')
        b.pack(side=LEFT, expand=0)
        b = Button(menuhull, text='<<',
                   command=lambda s=self: s.jump(-10))
        createToolTip(b, 'go back 10 (Alt-Ctl-PageUp)')
        b.pack(side=LEFT, expand=0)
        b = Button(menuhull, text='<',
                   command=lambda s=self: s.jump(-1))
        createToolTip(b, 'go back 1 (Alt-PageUp)')
        b.pack(side=LEFT, expand=0)
        b = Button(menuhull, text='>',
                   command=lambda s=self: s.jump(1))
        createToolTip(b, 'go forward 1 (Alt-PageDown)')
        b.pack(side=LEFT, expand=0)
        b = Button(menuhull, text='>>',
                   command=lambda s=self: s.jump(10))
        createToolTip(b, 'go forward 10 (Alt-Ctl-PageDown)')
        b.pack(side=LEFT, expand=0)
        b = Button(menuhull, text='>|',
                   command=lambda s=self: s.jump(1e6))
        createToolTip(b, 'go to end (Alt-Ctl-End)')
        b.pack(side=LEFT, expand=0)

        self.session = None
        self.jump(1e6)

    def selanimal(self, tk, animal):
        if self.session:
            self.session.save()
            self.session.destroy()
            self.session = None
        self.animal = animal
        self.jump(1e6)
        tk.winfo_toplevel().title('elog:%s' % animal)

    def jump(self, n, save=1):
        if self.session:
            n = self.session.n + n
            if save:
                self.session.save()
            self.session.destroy()

        self.session = SessionWindow(self, self.db, self.animal)
        self.session.pack(expand=1, fill=BOTH, anchor=N)
        self.session.n = n
        self.session.view()

    def exists(self, animal, date):
        rows = self.db.query("""SELECT sessionID, date FROM session"""
                             """ WHERE animal='%s' AND date='%s'"""
                             """ ORDER BY date""" %
                             (animal, date,))
        return len(rows) > 0

    def quit(self):
        self.save()
        self.db.close()
        self.destroy()

    def save(self):
        self.session.save()
        Msg("Saved.")
        return 1

    def view(self, date=None, exper=None):
        self.session.view(date=date)

    def next_exper(self):
        rows = self.db.query("""SELECT exper FROM exper"""
                             """ WHERE animal like '%s'"""
                             """ ORDER BY exper DESC LIMIT 1""" %
                             (self.animal,))
        pre = self.animal
        num = 0
        if len(rows) > 0:
            try:
                exper = rows[0]['exper']
                pre = exper[:-4]
                num = int(exper[-4:]) + 1
            except ValueError:
                pass
        guess = "%s%04d" % (pre, num)
        return ask(self, 'new exper', guess)

    def new_exper(self):
        exper = self.next_exper()
        if exper is None or len(exper) <= 0:
            return

        self.session.save()
        d = self.session.rv.getall()
        date = self.session.rv.getval('date')

        # insert empty new exper in the database
        self.db.query("""INSERT INTO exper (exper, animal, date, time)"""
                      """ VALUES %s""" %
                      ((exper, self.animal, date, time.strftime('%H%M-')),))

        link = "\n<elog:exper=%s/%s>\n" % (d['date'], exper)
        note = d['note'] + link

        rows = self.db.query("""SELECT sessionID FROM session"""
                             """ WHERE animal='%s' and date='%s'""" %
                             (d['animal'], d['date'],))
        sessionID = rows[0]['sessionID']

        # following command is the problem!! REPLACE deletes row
        # first.. should be UPDATE instead.. record already should
        # exist!
        self.db.query("""UPDATE session SET animal='%s', date='%s', note='%s'"""
                      """ WHERE sessionID=%d""" %
                       (d['animal'], d['date'],
                        str(note).replace("'", "\\'"), sessionID),)

        self.jump(0, save=0)

#############################################################3

def usage(badarg=None, exit=1):
    sys.stderr.write("""\
mlab database-backed electronic log notebook tool
usage: %s [options] [date] [exper]

General options:
  -info                    list animals in database to stdout (and exit)
  -q                       query animal and date info from user
  -animal=<animal name>    select animal *FULL NAME, NOT ABBREV*
  -new                     flag to allow creation of new animal
  -date                    query for date from user
  -date=YYYY-MM-DD         start new log entry if it doesn't exist
  -exper=PREFIXnnnnn       jump to day exper was done
  -today                   requires -animal as well!
  -ro                      read only mode!
  -dump[=N]                dump html to console; N<0 work backwards from now.
  -out=dir                 name of dump directory
  -rev                     reverse order of dump (ie, most recent first)
  -y                       force yes answer to create-new-entry questions
Datafile options:
  -data file1..fileN       add new datafiles to sql db (won't overwrite)
  -forcedata file1..fileN  add new datafiles, but overwrites existing records
""" % os.path.basename(sys.argv[0]))
    if badarg:
        sys.stderr.write(' Unknown option: "%s"\n' % badarg)
        sys.exit(1)
    if exit:
        sys.exit(1)

def animallist(db):
    s = string.join(find_animals(db), ' ')
    if len(s) > 0:
        return s
    else:
        return 'None'

def require_tk(tk):
    if tk is None:
        sys.stderr.write("Can't initialize GUI\n")
        sys.exit(0)

def start():
    import datetime, calendar

    if len(getuser()) == 0:
        sys.stderr.write('no user information available!\n')
        sys.exit(1)

    if len(gethost()) == 0:
        sys.stderr.write('no host/computer name available!\n')
        sys.exit(1)

    animal = None
    dump = None
    outdir = None
    rev = None
    date = None
    exper = None
    dfile = None
    files = []
    init = None                         # initialize fresh database
    readonly = None
    info = None
    new = 0
    force_yes = 0
    tk = None

    try:
        tk = Tk()
        tk.withdraw()
        Pmw.initialise(tk, size=8)
        tk.option_add("*Font", 'Helvetica 8')
        tk.option_add("*Entry.Font", 'Courier 8')
        tk.option_add("*Text.Font", 'Courier 8')
        tk.option_add("*DisabledForeground", 'black')
    except:
        tk = None

    for arg in sys.argv[1:]:
        if arg[0:2] == '--':
            arg = arg[1:]

        if isarg(arg, '-init'):
            init = 1
        elif isarg(arg, '-y'):
            force_yes = 1
        elif isarg(arg, '-ro'):
            readonly = 1
        elif isarg(arg, '-info'):
            info = 1
        elif isarg(arg, '-q'):
            require_tk(tk)
            animal = tkdialogs.select(find_animals(Database()))
            if animal is None:
                sys.exit(0)
            require_tk(tk)
            date = tkdialogs.getdate(tk)
            if date is None:
                sys.exit(0)
        elif isarg(arg, '-animal='):
            animal = string.split(arg, '=')[1]
        elif isarg(arg, '-animal'):
            require_tk(tk)
            animal = tkdialogs.select(find_animals(Database()))
            if animal is None:
                sys.exit(0)
        elif isarg(arg, '-a'):
            animal = arg[2:]
        elif isarg(arg, '-new'):
            new = 1
        elif isarg(arg, '-date='):
            date = string.split(arg, '=')[1]
        elif isarg(arg, '-date'):
            require_tk(tk)
            date = tkdialogs.getdate(tk)
            if date is None:
                sys.exit(0)
        elif isarg(arg, '-exper='):
            exper = string.split(arg, '=')[1]
        elif isarg(arg, '-today'):
            date = '%s' % datetime.date(1,1,1).today()
        elif isarg(arg, '-dump='):
            dump = 1
            count = int(string.split(arg, '=')[1])
        elif isarg(arg, '-dump'):
            dump = 1
            count = 0
        elif isarg(arg, '-out='):
            outdir = string.split(arg, '=')[1]
        elif isarg(arg, '-rev'):
            rev = 1
        elif isarg(arg, '-data'):
            dfile = 1
            force = None
        elif isarg(arg, '-forcedata'):
            dfile = 1
            force = 1
        elif isarg(arg, '-help'):
            usage()
        elif os.path.exists(arg):
            # datafile to add
            files.append(arg)
        elif re.match('^[0-9]...-[0-9].-[0-9].*/[a-z]*[0-9]...$', arg):
            date = arg[0:10]
            exper = arg[11:]
        elif re.match('^[a-z]*[0-9]...$', arg):
            exper = arg
        elif re.match('^[0-9]...-[0-9].-[0-9].*$', arg):
            date = arg
        else:
            animal = arg

    (_animal, _date) = cachestate()
    if not dump and animal is None:
        animal = _animal
    if not dump and date is None:
        date = _date

    if init:
        # initialize an empty database -- use with CAUTION!!!
        initdb.init_empty_db()
        sys.exit(0)

    db = Database()

    if info:
        sys.stdout.write(animallist(Database()))
        sys.stdout.write('\n')
        sys.exit(0)

    if dump and animal is None:
        sys.stderr.write("-dump requires -animal\n")
        sys.exit(0)

    if exper:
        (animal, date) = find_expers(Database(), exper)
        if animal is None:
            sys.exit(0)

    alist = find_animals(Database())
    if (animal not in alist):
        if (not new):
            sys.stderr.write("'%s' doesn't exist, use -new\n" % animal)
            sys.exit(0)
        else:
            if date is None:
                date = datetime.date(1,1,1).today()

    if dfile:
        find_pype()
        try:
            for f in files:
                if not insert_dfile(Database(), f, force=force):
                    sys.exit(1)
        finally:
            Database().close()
        sys.exit(0)

    if dump:
        if outdir is None:
            sys.stderr.write('must specify output directory with dump\n')
            sys.exit(1)
        dumphtml.dump(outdir, Database(),
                      animal, count, rev=rev, date=date)
        Database().close()
        sys.exit(0)

    Database().readonly = readonly

    require_tk(tk)

    app = GuiWindow(tk, Database(), animal=animal)

    if date:
        dow = ''
        try:
            # allow for date=-1 for yesterday, etc..
            x = int(date)
            d_ = (datetime.date.today() + datetime.timedelta(int(x)))
            realdate = '%s' % d_
            date = realdate
            dow = ' (%s)' % calendar.day_name[d_.weekday()]
        except ValueError:
            pass
        except TypeError:
            pass

        if not app.exists(animal=animal, date=date):
            if not force_yes:
                sys.stderr.write('animal=\'%s\' date=%s%s not in database.\n' % \
                                 (animal, date, dow))
            if animal is None:
                sys.stderr.write('Specify an animal to create new entry\n')
                sys.exit(1)
            else:
                if not force_yes and \
                       not askyesno('elog',
                                    "Create new entry: '%s' on %s%s?" % \
                                    (animal, date, dow)):
                    sys.exit(0)
                app.session.today(date=date)
                app.save()

    app.pack(fill=BOTH, expand=1, anchor=NW)

    #s = Label(tk, text="", anchor=E, fg='red', relief=FLAT)
    #s.pack(side=BOTTOM, expand=0, fill=X, anchor=W)

    #Msg(window=s)

    app.view(date=date)

    app.bind_all('<Alt-Control-KeyPress-q>', lambda e, tk=tk: die(tk))
    app.bind_all('<Control-KeyPress-s>', lambda e, w=app: w.save())
    app.bind_all('<Alt-KeyPress-s>', lambda e, w=app: w.save())
    app.bind_all('<Alt-KeyPress-g>', lambda e, w=app: w.find())
    app.bind_all('<Alt-KeyPress-n>', lambda e, w=app: w.new_exper())
    app.bind_all('<Alt-KeyPress-r>', lambda e, w=app: w.jump(0))
    app.bind_all('<Alt-KeyPress-Next>', lambda e, w=app: w.jump(1))
    app.bind_all('<Alt-KeyPress-Prior>', lambda e, w=app: w.jump(-1))
    app.bind_all('<Alt-Control-KeyPress-Next>', lambda e, w=app: w.jump(10))
    app.bind_all('<Alt-Control-KeyPress-Prior>', lambda e, w=app: w.jump(-10))
    app.bind_all('<Alt-Control-Home>', lambda e, w=app: w.jump(-1e6))
    app.bind_all('<Alt-Control-End>', lambda e, w=app: w.jump(1e6))

    tk.winfo_toplevel().title('elog:%s' % animal)
    tk.protocol("WM_DELETE_WINDOW", app.quit)
    tk.deiconify()
    tk.wait_window(app)
