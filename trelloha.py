#!/usr/bin/env python
import json
import logging
import netrc
import re

import requests
import trello

TRELLO_APP_KEY = "ec65a98b933f15b1fdb63dd79ef281b3"

LOG = logging.getLogger(__name__)


class NoAuth(RuntimeError):
    def __init__(self, trello):
        super(NoAuth, self).__init__(
            """No authentication token found.\n
Go to:\n%s\n\nand add the following to your ~/.netrc file:\n
machine trello.com login <BOARD_ID> password <TOKEN>""" % 
            trello.get_token_url("Trelloha",
                                 expires='30days',
                                 write_access=True))


class Trelloha(object):

    GERRIT_URL = "https://review.openstack.org"

    def __init__(self):
        self.trello = trello.TrelloApi(TRELLO_APP_KEY)
        self.board_id, token = self.get_board_token()
        self.trello.set_token(token)

    def get_board_token(self, site_name="trello.com", netrc_file=None):
        """Read a .netrc file and return login/password."""
        n = netrc.netrc(netrc_file)
        if site_name not in n.hosts:
            raise NoAuth(self.trello)
        return n.hosts[site_name][0], n.hosts[site_name][2]

    # TODO(jd) add that in trello.boards
    def checkitem_update_state(self, card_id, checklist_id, checkitem_id,
                               state):
        resp = requests.put(
            "https://trello.com/1/cards/%s/checklist/%s/checkItem/%s/state"
            % (card_id, checklist_id, checkitem_id),
            params=dict(key=self.trello._apikey, token=self.trello._token),
            data=dict(value=state))
        resp.raise_for_status()
        return json.loads(resp.content)

    def get_review(self, review_id):
        r = requests.get(
            "%s/changes/%d" % (self.GERRIT_URL, review_id))
        return json.loads(r.text[5:])

    def update_trello_card_checklist_with_review(self):
        for checklist in self.trello.boards.get_checklist(self.board_id):
            for item in checklist['checkItems']:
                if (item['state'] == "incomplete"
                   and self.GERRIT_URL in item['name']):
                    matched = re.search("%s/(#/c/)?(\d+)" % self.GERRIT_URL,
                                        item['name'])
                    if not matched:
                        continue
                    review = self.get_review(int(matched.group(2)))
                    if review['status'] == "MERGED":
                        LOG.info(
                            "Setting %s to complete, review %s is merged"
                            % (item['id'], review_id))
                        self.checkitem_update_state(checklist['idCard'],
                                                    checklist['id'],
                                                    item['id'],
                                                    "complete")


def main():
    t = Trelloha()
    t.update_trello_card_checklist_with_review()


if __name__ == '__main__':
    main()
