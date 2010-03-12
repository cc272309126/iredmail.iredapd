#!/usr/bin/env python
# encoding: utf-8

# Author: Zhang Huangbin <michaelbibby (at) gmail.com>

# ----------------------------------------------------------------------------
# This plugin is used for mail deliver restriction.
# ----------------------------------------------------------------------------

import sys

ACTION_REJECT = 'REJECT Not Authorized'

def __get_allowed_senders(ldapConn, ldapBaseDn, listDn, sender, recipient, policy,):
    """return search_result_list_based_on_access_policy"""

    basedn = ldapBaseDn
    searchScope = 2     # Use SCOPE_BASE to improve performance.

    # Set search base dn, scope, filter and attribute list based on access policy.
    if policy == 'membersonly':
        # Filter used to get domain members.
        searchFilter = "(&(|(objectclass=mailUser)(objectClass=mailExternalUser))(accountStatus=active)(memberOfGroup=%s))" % (recipient, )
        searchAttr = ['mail']
    elif policy == 'allowedonly':
        basedn = listDn
        searchScope = 0     # Use SCOPE_BASE to improve performance.
        # Filter used to get domain moderators.
        searchFilter = "(&(objectclass=mailList)(mail=%s))" % (recipient, )
        searchAttr = ['listAllowedUser']
    else:
        # Policy: membersAndAllowedOnly.
        # Filter used to get both members and moderators.
        searchFilter = "(|(&(|(objectClass=mailUser)(objectClass=mailExternalUser))(memberOfGroup=%s))(&(objectclass=mailList)(mail=%s)))" % (recipient, recipient, )
        searchAttr = ['mail', 'listAllowedUser']

    try:
        result = ldapConn.search_s(basedn, searchScope, searchFilter, searchAttr)
        userList = []
        for obj in result:
            for k in searchAttr:
                if k in obj[1].keys():
                    # Example of result data:
                    # [('dn', {'listAllowedUser': ['user@domain.ltd']})]
                    userList += obj[1][k]
                else:
                    pass
        return userList

    except Exception, e:
        return []

def restriction(ldapConn, ldapBaseDn, ldapRecipientDn, ldapRecipientLdif, smtpSessionData, **kargs):
    # Return if recipient is not a mail list object.
    if 'maillist' not in [ v.lower() for v in ldapRecipientLdif['objectClass']]:
        return 'DUNNO'

    sender = smtpSessionData['sender'].lower()
    recipient = smtpSessionData['recipient'].lower()
    policy = ldapRecipientLdif.get('accessPolicy', ['public'])[0].lower()

    if policy == "public": return 'DUNNO'   # No restriction.
    elif policy == "domain":
        # Bypass all users under the same domain.
        if sender.split('@')[1] == recipient.split('@')[1]: return 'DUNNO'
        else: return ACTION_REJECT
    else:
        # Handle other access policies: membersOnly, allowedOnly, membersAndAllowedOnly.
        allowedSenders = __get_allowed_senders(
                ldapConn=ldapConn,
                ldapBaseDn=ldapBaseDn,
                listDn=ldapRecipientDn,
                sender=sender,
                recipient=recipient,
                policy=policy,
                )

        if sender.lower() in [ v.lower() for v in allowedSenders ]:
            return 'DUNNO'
        else:
            return ACTION_REJECT