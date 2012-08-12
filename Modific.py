# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
import os
import threading
import subprocess
import functools
import re

# Just want to mention, at least half of the code
# was copy-pasted from the Git plugin https://github.com/kemayo/sublime-text-2-git
# open source is cool :)

settings = sublime.load_settings("Modific.sublime-settings")


def get_vcs_settings():
    return settings.get('vcs', [
        ["git", "git"],
        ["svn", "svn"],
        ["bzr", "bzr"],
        ["hg", "hg"]
    ])


def vcs_root(directory):
    """
    Determines root directory for VCS
    """

    vcs_check = [ (lambda vcs: lambda dir: os.path.exists(os.path.join(dir, '.' + vcs))
                                      and {'root': dir, 'name': vcs})(vcs)
                   for vcs, _ in get_vcs_settings() ]

    while directory:
        available = filter(lambda x: x, [check(directory) for check in vcs_check])
        if available:
            return directory, available[0]

        parent = os.path.realpath(os.path.join(directory, os.path.pardir))
        if parent == directory:
            # /.. == /
            return None, None
        directory = parent
    return None, None


def get_vcs(directory):
    """
    Determines, which of VCS systems we should use for given folder.
    Currently, uses priority of definitions in settings.get('vcs')
    """
    root_dir, vcs = vcs_root(directory)
    return vcs


def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)


def _make_text_safeish(text, fallback_encoding):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    try:
        return text.decode('utf-8')
    except UnicodeDecodeError:
        return text.decode(fallback_encoding)

def do_when(conditional, callback, *args, **kwargs):
    if conditional():
        return callback(*args, **kwargs)
    sublime.set_timeout(functools.partial(do_when, conditional, callback, *args, **kwargs), 50)


class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir="", fallback_encoding="", console_encoding="", **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        self.stdin = kwargs.get('stdin',None)
        self.stdout = kwargs.get('stdout',subprocess.PIPE)
        self.console_encoding = console_encoding
        self.fallback_encoding = fallback_encoding
        self.kwargs = kwargs

    def run(self):
        try:
            # Per http://bugs.python.org/issue8557 shell=True is required to
            # get $PATH on Windows. Yay portable code.
            shell = os.name == 'nt'
            if self.working_dir != "":
                os.chdir(self.working_dir)

            if self.console_encoding:
                self.command = [s.encode(self.console_encoding) for s in self.command]

            proc = subprocess.Popen(self.command,
                stdout=self.stdout, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                shell=shell, universal_newlines=True)
            output = proc.communicate(self.stdin)[0]
            if not output:
                output = ''
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done,
                _make_text_safeish(output, self.fallback_encoding), **self.kwargs)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, e.returncode)
        except OSError, e:
            if e.errno == 2:
                main_thread(sublime.error_message,
                    "'%s' binary could not be found in PATH\n\nConsider using the vcs_command to specify PATH\n\nPATH is: %s" % (self.command[0], os.environ['PATH']))
            else:
                raise e


class VcsCommand(object):
    may_change_files = False

    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs['fallback_encoding'] = self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]
        kwargs['console_encoding'] = settings.get('console_encoding')

        autosave = settings.get('autosave', True)
        if self.active_view() and self.active_view().is_dirty() and autosave:
            self.active_view().run_command('save')
        if not callback:
            callback = self.generic_done

        thread = CommandThread(command, callback, **kwargs)
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)

    def generic_done(self, result):
        if self.may_change_files and self.active_view() and self.active_view().file_name():
            if self.active_view().is_dirty():
                result = "WARNING: Current view is dirty.\n\n"
            else:
                # just asking the current file to be re-opened doesn't do anything
                print "reverting"
                position = self.active_view().viewport_position()
                self.active_view().run_command('revert')
                do_when(lambda: not self.active_view().is_loading(), lambda: self.active_view().set_viewport_position(position, False))

        if not result.strip():
            return
        self.panel(result)

    def _output_to_view(self, output_file, output, clear=False,
            syntax="Packages/Diff/Diff.tmLanguage"):
        output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def scratch(self, output, title=False, position=None, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        if position:
            sublime.set_timeout(lambda: scratch_file.set_viewport_position(position), 0)
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("vcs")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.vcs"})

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    def active_view(self):
        return self.view

    def get_window(self):
        if (hasattr(self, 'view') and hasattr(self.view, 'window')):
            return self.view.window()
        else:
            return sublime.active_window()

    def get_working_dir(self):
        return os.path.dirname(self._active_file_name())

    def is_enabled(self):
        if self._active_file_name():
            return get_vcs(self.get_working_dir())

    def get_user_command(self, vcs_name):
        return dict(get_vcs_settings()).get(vcs_name, False)


class DiffCommand(VcsCommand):
    """ Here you can define diff commands for your VCS
        method name pattern: %(vcs_name)s_diff_command
    """

    def run(self, edit):
        vcs = get_vcs(self.get_working_dir())
        filename = os.path.basename(self.view.file_name())
        get_command = getattr(self, '{0}_diff_command'.format(vcs['name']), None)
        if get_command:
            self.run_command(get_command(filename), self.diff_done)

    def diff_done(self, result):
        pass

    def git_diff_command(self, file_name):
        return [self.get_user_command('git') or 'git', 'diff', '--no-color', '--', file_name]

    def svn_diff_command(self, file_name):
        return [self.get_user_command('svn') or 'svn', 'diff', '--internal-diff', file_name]

    def bzr_diff_command(self, file_name):
        return [self.get_user_command('bzr') or 'bzr', 'diff', file_name]

    def hg_diff_command(self, file_name):
        return [self.get_user_command('hg') or 'hg', 'diff', file_name]


class ShowDiffCommand(DiffCommand, sublime_plugin.TextCommand):
    def diff_done(self, result):
        if not result.strip():
            return

        file_name = re.findall(r'([^\\\/]+)$', self.view.file_name())
        self.scratch(result, title="Diff - " + file_name[0])


class DiffParser(object):
    instance = None

    def __init__(self, diff):
        self.diff = diff
        self.chunks = None
        self.__class__.instance = self

    def _append_to_chunks(self, start, lines):
        self.chunks.append({
            "start": start,
            "end": start + len(lines),
            "lines": lines
        })

    def get_chunks(self):
        if self.chunks is None:
            self.chunks = []
            diff = self.diff.strip()
            if diff:
                re_header = re.compile(r'^@@[0-9\-, ]+\+(\d+)', re.S)
                current = None
                lines = []
                for line in diff.splitlines():
                    # ignore lines with '\' at the beginning
                    if line[0] == '\\':
                        continue

                    matches = re.findall(re_header, line)
                    if matches:
                        if current is not None:
                            self._append_to_chunks(current, lines)
                        current = int(matches[0])
                        lines = []
                    elif current:
                        lines.append(line)
                if current is not None and lines:
                    self._append_to_chunks(current, lines)

        return self.chunks

    def get_lines_to_hl(self):
        inserted = []
        changed = []
        deleted = []

        for chunk in self.get_chunks():
            current = chunk['start']
            deleted_line = None
            for line in chunk['lines']:
                if line[0] == '-':
                    if (not deleted_line or deleted_line not in deleted):
                        deleted.append(current)
                    deleted_line = current
                elif line[0] == '+':
                    if deleted_line:
                        deleted.pop()
                        deleted_line = None
                        changed.append(current)
                    elif current - 1 in changed:
                        changed.append(current)
                    else:
                        inserted.append(current)
                    current += 1
                else:
                    deleted_line = None
                    current += 1

        return inserted, changed, deleted

    def get_original_part(self, line_num):
        """ returns a chunk of code that relates to the given line
            and was there before modifications

            return (lines list, start_line int, replace_lines int)
        """

        for chunk in self.get_chunks():
            if chunk['start'] <= line_num <= chunk['end']:
                ret_lines = []
                current = chunk['start']
                first = None
                replace_lines = 0
                return_this_lines = False
                for line in chunk['lines']:
                    if line[0] == '-' or line[0] == '+':
                        first = first or current
                        if current == line_num:
                            return_this_lines = True
                        if line[0] == '-':
                            ret_lines.append(line[1:])
                        else:
                            replace_lines += 1
                            current += 1
                    elif return_this_lines:
                        break
                    else:
                        current += 1
                        ret_lines = []
                if return_this_lines:
                    return ret_lines, first, replace_lines

        return None, None, None


class HlChangesCommand(DiffCommand, sublime_plugin.TextCommand):
    def hl_lines(self, lines, hl_key):
        if (not len(lines)):
            self.view.erase_regions(hl_key)
            return

        icon = settings.get('region_icon') or 'dot'
        points = [self.view.text_point(l - 1, 0) for l in lines]
        regions = [sublime.Region(p, p) for p in points]
        self.view.add_regions(hl_key, regions, "markup.%s.diff" % hl_key,
            icon, sublime.HIDDEN | sublime.DRAW_EMPTY)

    def diff_done(self, diff):
        if diff and '@@' not in diff:
            # probably this is an error message
            print diff

        diff_parser = DiffParser(diff)
        (inserted, changed, deleted) = diff_parser.get_lines_to_hl()

        if settings.get('debug'):
            print inserted, changed, deleted
        self.hl_lines(inserted, 'inserted')
        self.hl_lines(deleted, 'deleted')
        self.hl_lines(changed, 'changed')


class ShowOriginalPartCommand(DiffCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        diff_parser = DiffParser.instance
        if not diff_parser:
            return

        (row, col) = self.view.rowcol(self.view.sel()[0].begin())
        (lines, start, replace_lines) = diff_parser.get_original_part(row + 1)
        if lines is not None:
            self.panel(os.linesep.join(lines))


class ReplaceModifiedPartCommand(DiffCommand, sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command('save')

        diff_parser = DiffParser.instance
        if not diff_parser:
            return

        (row, col) = self.view.rowcol(self.view.sel()[0].begin())
        (lines, current, replace_lines) = diff_parser.get_original_part(row + 1)
        if settings.get('debug'):
            print 'replace', (lines, current, replace_lines)
        if lines is not None:
            edit = self.view.begin_edit()
            try:
                begin = self.view.text_point(current - 1, 0)
                content = os.linesep.join(lines)
                if replace_lines:
                    end = self.view.line(self.view.text_point(replace_lines + current - 2, 0)).end()
                    region = sublime.Region(begin, end)
                    if lines:
                        self.view.replace(edit, region, content)
                    else:
                        region = self.view.full_line(region)
                        self.view.erase(edit, region)
                else:
                    self.view.insert(edit, begin, content + os.linesep)
                self.view.run_command('save')
            finally:
                self.view.end_edit(edit)


class HlChangesBackground(sublime_plugin.EventListener):
    def on_load(self, view):
        view.run_command('hl_changes')

    def on_activated(self, view):
        view.run_command('hl_changes')

    def on_post_save(self, view):
        view.run_command('hl_changes')


class JumpBetweenChangesCommand(DiffCommand, sublime_plugin.TextCommand):
    def run(self, edit, direction='next'):
        lines = self._get_lines()
        if not lines:
            return

        if direction == 'prev':
            lines.reverse()

        (current_line, col) = self.view.rowcol(self.view.sel()[0].begin())
        current_line += 1
        jump_to = None
        for line in lines:
            if direction == 'next' and current_line < line:
                jump_to = line
                break
            if direction == 'prev' and current_line > line:
                jump_to = line
                break

        if not jump_to:
            jump_to = lines[0]

        self.goto_line(edit, jump_to)

    def goto_line(self, edit, line):
        # Convert from 1 based to a 0 based line number
        line = int(line) - 1

        # Negative line numbers count from the end of the buffer
        if line < 0:
            lines, _ = self.view.rowcol(self.view.size())
            line = lines + line + 1

        pt = self.view.text_point(line, 0)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pt))

        self.view.show(pt)

    def _get_lines(self):
        diff_parser = DiffParser.instance
        if not diff_parser:
            return

        (inserted, changed, deleted) = diff_parser.get_lines_to_hl()
        lines = list(set(inserted + changed + deleted))
        lines.sort()

        prev = None
        ret_lines = []
        for line in lines:
            if prev != line - 1:
                ret_lines.append(line)
            prev = line

        return ret_lines


class UncommittedFilesCommand(VcsCommand, sublime_plugin.WindowCommand):
    def active_view(self):
        return self.window.active_view()

    def run(self):
        self.root, self.vcs = vcs_root(self.get_working_dir())
        status_command = getattr(self, '{0}_status_command'.format(self.vcs['name']), None)
        if status_command:
            self.run_command(status_command(), self.status_done, working_dir=self.root)

    def git_status_command(self):
        return [self.get_user_command('git') or 'git', 'status', '--porcelain']

    def svn_status_command(self):
        return [self.get_user_command('svn') or 'svn', 'status', '--quiet']

    def bzr_status_command(self):
        return [self.get_user_command('bzr') or 'bzr', 'status', '-S', '--no-pending', '-V']

    def hg_status_command(self):
        return [self.get_user_command('hg') or 'hg', 'status']

    def git_status_file(self, file_name):
        # first 2 characters are status codes, the third is a space
        return file_name[3:]

    def svn_status_file(self, file_name):
        return file_name[8:]

    def bzr_status_file(self, file_name):
        return file_name[4:]

    def hg_status_file(self, file_name):
        return file_name[2:]

    def status_done(self, result):
        self.results = filter(lambda x: len(x) > 0 and not x.lstrip().startswith('>'),
            result.rstrip().split('\n'))
        if len(self.results):
            self.show_status_list()
        else:
            sublime.status_message("Nothing to show")

    def show_status_list(self):
        self.get_window().show_quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_file = self.results[picked]
        get_file = getattr(self, '{0}_status_file'.format(self.vcs['name']), None)
        if (get_file):
            self.open_file(get_file(picked_file))

    def open_file(self, picked_file):
        if os.path.isfile(os.path.join(self.root, picked_file)):
            self.window.open_file(os.path.join(self.root, picked_file))
        else:
            sublime.status_message("File doesn't exist")
