#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Log monitoring and capture.
"""
from builtins import next
from builtins import str
from builtins import object
import posixpath
import itertools
import logging
import plumbum


logger = logging.getLogger('logwatch')


def get_ssh(ctl):
    """Acquire the ssh connection from a role ctl.
    """
    return ctl.ssh if getattr(ctl.ssh, '_session', None) else ctl.ssh()


class logfiles(object):
    """A log capture source for files found at a remote location.
    """
    def __init__(self, ctl, *tables):
        self.ctl = ctl
        self.ssh = get_ssh(ctl)
        self.logtable = tables
        self.ident = ctl.hostname

    def iterlogs(self):
        """Iterate through all log rotation based variations of a log
        that exists. """
        def numbered_log(ctl, logdir, logname):
            remote = self.ssh.path(logdir)
            remote_log = remote.join(logname)
            if not remote_log.exists():
                return
            yield remote_log

            # Should (it shouldn't) discontinuous numbering happen for
            # any reason, we won't notice. Might cause problems.
            # Hopefully not something we'll have to deal with...
            for idx in itertools.count(1):
                remote_log = remote.join(posixpath.extsep.join(
                    (logname, str(idx))))
                if not remote_log.exists():
                    return
                yield remote_log

        for logdir, logfiles in self.logtable:
            for logfile in logfiles:
                # This yields another generator. I did not intend for this
                # to be a yield from
                yield numbered_log(self.ctl, logdir, logfile)

    def prepare(self):
        """Prepare by truncating all existing logs."""
        logger.info('Truncating logs for {}'.format(self.ident))
        for logset in self.iterlogs():
            log = next(logset, None)
            if not log:
                continue

            log.write('')  # Truncate by replacing it with an empty file
            for log in logset:
                log.unlink()

    def capture(self):
        """Capture logs for provided controller."""
        logger.info('Capturing logs for {}'.format(self.ident))
        for log in itertools.chain.from_iterable(self.iterlogs()):
            if log.stat().st_size > 0:
                logger.debug('Captured {} for {}'.format(
                    log.name, self.ident
                ))
                yield log, log.read()


class journal(object):
    """A log capture source for a systemd service at a remote location.
    """
    def __init__(self, ctl, unit):
        self.ctl = ctl
        self.ssh = get_ssh(ctl)
        self.unit = unit
        self.timestamp = self.ssh['date']('+%Y-%m-%d %H:%M:%S').strip()
        self.journalctl = self.ssh['journalctl']

    def prepare(self):
        self.timestamp = self.ssh['date']('+%Y-%m-%d %H:%M:%S').strip()

    def capture(self):
        try:
            logger.info("Capturing journal log since {}".format(
                self.timestamp))
            log = self.journalctl('--unit', self.unit,
                                  '--since', self.timestamp)
            yield self.unit, log
        except plumbum.ProcessExecutionError as err:
            if '-- Logs begin at' not in err.stdout:
                logger.exception("Failed to capture journal log")
