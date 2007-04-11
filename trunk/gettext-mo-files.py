from os import listdir, spawnl, P_WAIT, makedirs
from os.path import basename, normpath
from glob import glob

def make_mo_gettext():
    """
    Calls 'msgfmt' from GNU gettext to genearte object files (.mo) from
    the translation files (.po).
    """
    print "Generating gettext mo files: "
    po_files = 'po/*.po'
    mo_base_dir = 'locale/%s/LC_MESSAGES/'
    conv_program = 'msgfmt'

    for lang_file in glob(po_files):
        language = basename(lang_file)[:-3]
        mo_dir = mo_base_dir % language
        print language + " "
        try:
            makedirs(mo_dir)
        except OSError, inst:
            if inst.strerror != 'File exists':
                print 'Warning: ', inst.file, inst.strerror, 'ignoring.'
        print lang_file, "+", mo_dir    # debugging
        # normalize path for windows #
        lang_file_norm = normpath(lang_file)
        mo_dir_norm = normpath(mo_dir)
        #
        spawnl(P_WAIT, conv_program, lang_file_norm, "-o", mo_dir_norm)
    print "done"


make_mo_gettext()
