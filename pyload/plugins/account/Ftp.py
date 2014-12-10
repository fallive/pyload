# -*- coding: utf-8 -*-

from pyload.plugins.Account import Account


class Ftp(Account):
    __name__    = "Ftp"
    __type__    = "account"
    __version__ = "0.01"

    __description__ = """Ftp dummy account plugin"""
    __license__     = "GPLv3"
    __authors__     = [("zoidberg", "zoidberg@mujmail.cz")]


    login_timeout  = -1  #: Unlimited
    info_threshold = -1  #: Unlimited