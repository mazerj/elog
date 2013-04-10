#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; py-indent-offset: 4; -*-

import string, textwrap, re, sys, time
from tools import *
import os, posixpath

LINEWIDTH=70

class FormatError:
    """Holder for formatting errors so they can be inserted at the
    head of the html dump at the end (basically a simple buffer).
    """
    _buf = []
    def __init__(self, errormsg=None):
        if errormsg:
            FormatError._buf.append(errormsg)

    def get(self):
        return FormatError._buf

def F(fmt, s):
    """Convert value->str using specified format string,
    '#' for missing data
    """
    if fmt == "%s" and len(s) == 0:
        return "<i>ND</i>"
    else:
        try:
            return fmt % s
        except TypeError:
            return "<i>ND</i>"

def YN(bool, yes='yes', no='no'):
    if bool: return yes
    else: return no

def nlsqueeze(s):
    """reduce all multi-nl sequences to single blank line (force terminal NL)"""
    while len(s) > 0 and s[-1] == '\n':
        s = s[:-1]
    while 1:
        s2 = string.replace(s, '\n\n\n', '\n\n')
        if len(s) == len(s2):
            return s2
        s = s2

def wrap(s):
    new = []
    for l in s.split('\n'):
        if len(l) < LINEWIDTH:
            new.append(l)
        else:
            for l in textwrap.wrap(l, width=LINEWIDTH,
                                   expand_tabs=True,
                                   subsequent_indent='  '):
                new.append(l)
    s = string.join(new, '\n');
    s = string.replace(s, ' ', '&nbsp;')
    return string.replace(s, '\n', '\n<br>\n')

def emit_session(outdir, db, r):
    """generate string resentation of NOTE record"""

    try:
        r['total'] = F("%d", r['water_work'] + r['water_sup'])
    except TypeError:
        r['total'] = F("%d", None)

    r['water_work'] = F("%d", r['water_work'])
    r['water_sup'] = F("%d", r['water_sup'])
    r['food'] = F("%d", r['food'])
    r['note'] = nlsqueeze(wrap(r['note']))
    r['fruit'] = F("%s", r['fruit'])

    s = ""
    s = s + \
        """<table class="tab_session">\n""" \
        """  <tr><td>\n""" \
        """    <table class="tab_sessioninfo">\n""" \
        """      <tr><td align="RIGHT"><b>DATE</b>:</td><td>%(date)s</td></tr>\n""" \
        """      <tr><td align="RIGHT"><b>ANIMAL</b>:</td><td>%(animal)s</td></tr>\n""" \
        """      <tr><td align="RIGHT"><b>USER</b>:</td><td>%(user)s</td></tr>\n""" \
        """      <tr><td align="RIGHT"><b>WATER</b>:</td><td>%(water_work)s/%(water_sup)s ml [=%(total)s ml]</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>FRUIT</b>:</td><td>%(fruit)s</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>FOOD</b>:</td> <td>%(food)s biscs</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>WEIGHT</b>:</td><td>%(weight)s kg</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>RESTRICTED</b>:</td><td>%(restricted)s</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>TESTED</b>:</td><td>%(tested)s</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>NCORRECT</b>:</td><td>%(ncorrect)s</td> </tr>\n""" \
        """      <tr><td align="RIGHT"><b>NTRIALS</b>:</td><td>%(ntrials)s</td> </tr>\n""" \
        """    </table>\n""" \
        """  </td></tr>\n""" \
        """  <tr><td>\n""" \
        """%(note)s\n""" \
        """  </td></tr>\n""" \
        """</table>\n""" % r

    # expand 'exper' hyperlinks iteratively until there are no more..
    while 1:
        links = re.findall('<elog:exper=.*>', s)
        if len(links) == 0: break

        link = links[0]
        x = string.find(s, link)
        before = s[:x]
        after = s[(x+len(link)):]
        datestr, exper = string.split(string.split(link[1:-1], '=')[1], '/')
        rows = db.query("""SELECT * FROM exper
        WHERE animal='%s' AND date='%s' AND exper='%s'
        """ % (r['animal'], r['date'], exper))

        if len(rows) == 0:
            s = before + """<b style="background-color:red">[DEADEND EXPER LINK: %s]</b>\n""" % link[1:-1] + after
            sys.stderr.write("deadend link warning: '%s'\n" % link)
            FormatError("deadend link warning: '%s'\n" % link)
        elif len(rows) > 1:
            # this should NEVER happen!
            s = before + """<b style="background-color:red">[MULTIPLE EXPER LINK: %s]</b>\n""" % link[1:-1] + after
            sys.stderr.write("multiple link warning: '%s'\n" % link)
            FormatError("multiple link warning: '%s'\n" % link)
        else:
            # expand link into html and splice back
            e = emit_exper(outdir, db, rows[0])
            s = before + e + after

    # expand 'dfile' hyperlinks
    while 1:
        # find links
        links = re.findall('<elog:dfile=.*>', s)
        if len(links) == 0:
            # no more links, we're done..
            break

        # find the location of the first link
        link = links[0]
        x = string.find(s, link)
        before = s[:x]
        after = s[(x+len(link)):]
        datestr, dfile = string.split(string.split(link[1:-1], '=')[1], '/')
        rows = db.query("""
        SELECT * FROM dfile
        WHERE animal='%s' AND date='%s' AND src LIKE '%%%s'
        """ % (r['animal'], r['date'], dfile))
        if len(rows) == 0:
            s = before + "<BAD LINK: %s>" % link[1:-1] + after
            sys.stderr.write("bad DFILE link warning: '%s'\n" % link)
            FormatError("bad DFILE link warning: '%s'\n" % link)
        else:
            if rows[0]['crap']:
                newlink = "-> %s (CRAP):" % (dfile,)
            else:
                newlink = "-> %s (OK):" % (dfile,)
            s = before + newlink + after

    s = string.strip(s, '\n')

    return s

def emit_exper(outdir, db, r):
    """generate string resentation of EXPR record"""

    if r['deleted']:
        return """<br><del>%(exper)s</del>"""
        
    r['note'] = nlsqueeze(wrap(r['note']))

    s = "" \
        """<br>\n""" \
        """<table class="tab_exper">\n""" \
        """  <tr>\n""" \
        """    <td>\n""" \
        """      <table class="tab_experinfo">\n""" \
        """        <tr>\n""" \
        """          <td align="RIGHT"><b>EXPER</b>:</td> <td>%(exper)s</td>\n""" \
        """        </tr>\n""" \
        """        <tr>\n""" \
        """          <td align="RIGHT"><b>TIME</b>:</td> <td>%(time)s</td>\n""" \
        """        </tr>\n""" \
        """      </table>\n""" \
        """    </td>\n""" \
        """  </tr>\n""" \
        """  <tr>\n""" \
        """    <td>\n""" \
        """%(note)s\n""" \
        """    </td>\n""" \
        """  </tr>\n""" % r

    rows = db.query("""
    SELECT * FROM unit
    WHERE exper='%s' and date like '%s' ORDER BY unitID
    """ % (r['exper'], r['date'], ))
    if len(rows) > 0:
        # one table row per unit
        for u in rows:
            s = s + """<tr> <td> %s </td> </tr>\n""" % emit_unit(outdir, db, u)

    rows = db.query("""
    SELECT * FROM dfile
    WHERE date='%s' and exper='%s' ORDER BY src
    """ % (r['date'], r['exper'], ))
    if len(rows) > 0:
        s = s + """<tr> <td> %s </td> </tr>\n""" % emit_dfiles(outdir, db, rows)
    s = s + """\n</table>\n"""
    return s

def emit_dfiles(outdir, db, rows):
    s = "" \
        """<table class="tab_dfile">\n""" \
        """  <tr> <th>pref</th> <th>src</th> <th>notes</th> </tr>\n\n"""

    rows.sort(None, lambda s: int(s['src'].split('.')[-1]))

    alist = []
    for d in rows:
        for a in d['attachlist'].split(','):
            if len(a) > 0:
                alist.append(a)

        d['preferred'] = YN(d['preferred'],'*',' ')
        d['note'] = nlsqueeze(wrap(d['note']))

        if d['crap']:
            # strike out filename if crap flag is set
            d['src'] = '<del>' + d['src'] + '</del>'

        l = "" \
            """<tr>\n""" \
            """  <td>%(preferred)s</td>\n""" \
            """  <td align="RIGHT">%(src)s</td>\n""" \
            """  <td>%(note)s</td>\n""" \
            """</tr>\n""" % d \

        s = s + l


    s = s + """</table>\n"""

    if len(alist) > 0:
        n = 1
        for id in alist:
            s = s + """<br>\n"""
            s = s + """<table class="tab_att">\n"""
            s = s + """ <tr><td>\n"""
            s = s + emit_attachment(outdir, db, id, 'ID#%s' % (id,))
            s = s + """ </td></tr>\n"""
            s = s + """</table>\n"""
            n = n + 1

    return s

def emit_attachment(outdir, db, id, tag):
    rows = db.query("""
    SELECT * FROM attachment WHERE attachmentID=%s
    """ % (id,))
    row = rows[0]

    img = row['data'].decode('base64')
    fname = 'a%05d.jpg' % int(id)
    open(outdir + '/' + fname , 'w').write(img)

    if len(row['title']) == 0:
        row['title'] = 'no title'

    # note: when you print, images don'ts seem to cross page boundaries!
    s = ""
    s = s + """<table>\n"""
    s = s + """ <tr><td>\n"""
    s = s + tag + """ [%(user)s:%(date)s] %(title)s""" % row
    s = s + """ </td></tr>\n"""
    if len(row['note']):
        s = s + """ <tr><td>\n"""
        s = s + tag + """%(note)s\n""" % row
        s = s + """ </td></tr>\n"""
    s = s + """ <tr><td>\n"""
    s = s + """  <img class="attachimg" src="%s">\n""" % fname
    s = s + """ </td></tr>\n"""
    s = s + """</table>\n"""

    return s

def emit_unit(outdir, db, r):
    """generate string resentation of UNIT record"""
    try:
        r['e'] = F('%0.f', ((r['rfx'] ** 2) + (r['rfy'] ** 2))**0.5)
    except TypeError:
        r['e'] = F('%0.f', None)

    r['crap'] = YN(r['crap'],'bad','good')
    r['rfx'] = F("%.0f", r['rfx'])
    r['rfy'] = F("%.0f", r['rfy'])
    r['rfr'] = F("%.0f", r['rfr'])
    r['ori'] = F("%.0f", r['ori'])
    r['color'] = F("%s", r['color'])

    r['note'] = nlsqueeze(wrap(r['note']))

    s = "" \
        """<table class="tab_unit" bgcolor="#e0e0e0">\n""" \
        """  <tr>\n""" \
        """    <td>\n""" \
        """      <table>\n""" \
        """        <tr> <td align="RIGHT"><b>UNIT</b>:</td>   <td> %(exper)s.%(unit)s</td>            </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>WELL</b>:</td>   <td> %(well)s (%(wellloc)s)</t          </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>AREA</b>:</td>   <td> %(area)s</td>                      </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>DEPTH</b>:</td>  <td> %(depth)s um</td>                  </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>CRAP</b>:</td>   <td> %(crap)s</td>                      </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>RF</b>:</td>     <td> (%(rfx)s, %(rfy)s) e=%(e)s px</td> </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>ORI</b>:</td>    <td> %(ori)s deg</td>                   </tr>\n""" \
        """        <tr> <td align="RIGHT"><b>COLOR</b>:</td>  <td> %(color)s</td>                     </tr>\n""" \
        """      </table>\n""" \
        """    </td></tr>\n""" \
        """  <tr>\n""" \
        """    <td>\n""" \
        """      %(note)s""" \
        """</td></tr>\n""" \
        """</table>\n""" % r
    return s

def dump(outdir, db, animal, count, rev=None, date=None):
    if date is None:
        date = ''
    else:
        date = "AND date LIKE '%s'" % date

    rows = db.query("""\
    SELECT * FROM session WHERE animal LIKE '%s' %s ORDER BY date""" \
                          % (animal, date,))

    if len(rows) == 0:
        sys.stderr.write("No matches for: animal='%s'\n" % animal)
        return

    if count > 0:
        rows = rows[:count]
    elif count < 0:
        rows = rows[count:]

    if rev:
        rows.reverse()

    if not posixpath.exists(outdir):
        os.mkdir(outdir)
    elif not posixpath.isdir(outdir):
        sys.stderr.write("Error creating %s\n" % outdir)
        return

    out = open(outdir+'/index.html', 'w')

    out.write("""<style type="text/css">\n"""
              """  .button { margin-left:5; margin-right:5}\n"""
              """  .tab_session { width:100%;\n"""
              """                 margin-top:5;margin-bottom:5;\n"""
              """                 background:#f0f0f0; border:0px solid black}\n"""
              """  .tab_sessioninfo { background: #f0f0f0; }\n"""
              """  .tab_exper { background: #e0e0e0; border:0px solid blue}\n"""
              """  .tab_experinfo { background: #e0e0e0; }\n"""
              """  .tab_unit { background: #d0d0d0; }\n"""
              """  .tab_dfile { background: #c0c0c0; }\n"""
              """  .tab_att { background: #c0c0c0; border:1px solid black}\n"""
              """  .attachimg { max-width: 600px; }\n"""
              """  table { border:0px solid black; }\n"""
              """  body { font-family: monospace; }\n"""
              """  @media print { .navbar { display:none; }\n"""
              """                  .attachimg { max-height: 2.5in; } }\n"""
              """</style>\n""")
    if 0:
        out.write("""dump at: %s<br>\n"""
                  """animal=<%s> count=<%s> rev=<%s> date=<%s><hr>\n""" %
                  (time.ctime(time.time()), animal, count, rev, date,))

    # highlight filenames and output
    p = re.compile("([a-z]*[0-9][0-9][0-9][0-9]\\.[a-z]*\\.[0-9][0-9][0-9])")
    outbuf = ""
    n = 0
    for session in rows:
        try:
            txt = emit_session(outdir, db, session)
            txt = nlsqueeze(txt)
            txt = p.sub("<b>\g<1></b>\n", txt);

            outbuf += """<DIV CLASS="navbar"; style="width:100%; background:lightblue">\n"""
            outbuf += """<A NAME="sess%d">\n""" % n
            outbuf += """<A CLASS="button" HREF="#sess%d">[first]</A> """ % (0,)
            outbuf += """<A CLASS="button" HREF="#sess%d">[prev session]</A> """ % (max(0,n-1),)
            outbuf += """<A CLASS="button" HREF="#sess%d">[next session]</A>\n""" % (min(len(rows)-1,n+1),)
            outbuf += """<A CLASS="button" HREF="#sess%d">[last]</A> """ % (len(rows)-1,)
            outbuf += """</DIV>\n"""
            outbuf += txt
            n = n + 1
        except IOError:
            sys.stderr.write("fatal error -- aborting\n")
            sys.exit(1)

    errs = FormatError().get()
    if len(errs):
        s = string.join(errs, '\n')
        s = string.replace(s, '>', '&gt')
        s = string.replace(s, '<', '&lt')
        out.write("<h2>%d Dump Error(s)</h2>\n" % (len(errs),))
        out.write("<PRE>\n%s\n</PRE><hr>\n" % s)

    out.write(outbuf)
    out.close()

    return 1

