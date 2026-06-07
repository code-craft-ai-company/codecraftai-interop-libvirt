"""
    .. module:: libvirtauthcallback
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Adapter translating a credential map into the callback
               tuple expected by ``libvirt.openAuth``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional


# libvirt credential-type integers (mirrors libvirt.VIR_CRED_*).  Declared
# locally so this module does not require the native bindings to import.
_CRED_USERNAME = 1
_CRED_AUTHNAME = 2
_CRED_PASSPHRASE = 3
_CRED_NOECHOPROMPT = 8


class LibvirtAuthCallback:
    """
        Adapter delivering SASL / SSH credentials to ``libvirt.openAuth``.

        ``libvirt.openAuth`` expects an ``[credtypes, callable, payload]``
        list.  This class wraps a static credential map so the callback
        can answer username / password prompts without interactive I/O.
    """

    def __init__(self, *, username: Optional[str] = None,
                 password: Optional[str] = None) -> None:
        """
            Construct a LibvirtAuthCallback.

            :param username: Optional username answer for username /
                authname prompts.
            :param password: Optional password answer for passphrase /
                no-echo prompts.
        """
        self._username: Optional[str] = username
        self._password: Optional[str] = password
        return

    def answer(self, *, credentials: List[Dict[str, Any]],
               user_data: Any) -> int:
        """
            Answer a batch of libvirt credential prompts.

            :param credentials: A list of prompt dicts; each is mutated
                in place with a ``result`` key.
            :param user_data: Opaque user data (unused).

            :returns: ``0`` on success, as libvirt requires.
        """
        for credential in credentials:
            cred_type = credential.get("type", None)
            if cred_type in (_CRED_USERNAME, _CRED_AUTHNAME):
                credential["result"] = self._username
            elif cred_type in (_CRED_PASSPHRASE, _CRED_NOECHOPROMPT):
                credential["result"] = self._password
            else:
                credential["result"] = None
        rtnval = 0
        return rtnval

    def as_openauth_argument(self) -> List[Any]:
        """
            Return the ``auth`` argument for ``libvirt.openAuth``.

            :returns: A ``[credtypes, callable, payload]`` list.
        """
        cred_types = [_CRED_USERNAME, _CRED_AUTHNAME,
                      _CRED_PASSPHRASE, _CRED_NOECHOPROMPT]

        def _bridge(creds: List[Dict[str, Any]], data: Any) -> int:
            result = self.answer(credentials=creds, user_data=data)
            return result

        rtnval = [cred_types, _bridge, None]
        return rtnval
