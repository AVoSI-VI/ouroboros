import apprise
import gettext

from logging import getLogger
from babel import dates
from pytz import timezone

class NotificationManager(object):
    def __init__(self, config, data_manager):
        self.config = config
        self.data_manager = data_manager
        self.logger = getLogger()

        self.apprise = self.build_apprise()
        self._ = None

        try:
            language = gettext.translation('notifiers', localedir='locales', languages=self.config.language)
            language.install()
            self._ = language.gettext
        except FileNotFoundError:
            if not self.config.language == 'en':
                self.logger.error("Can't find the '%s' language", self.config.language)
            self._ = gettext.gettext

    def build_apprise(self):
        asset = apprise.AppriseAsset(
            image_url_mask='https://raw.githubusercontent.com/gmt2001/ouroboros/main/assets/ouroboros_logo_icon_72.png',
            default_extension='.png'
        )
        asset.app_id = "Ouroboros"
        asset.app_desc = "Ouroboros"
        asset.app_url = "https://github.com/gmt2001/ouroboros"
        asset.html_notify_map['info'] = '#5F87C6'
        asset.image_url_logo = 'https://raw.githubusercontent.com/gmt2001/ouroboros/main/assets/ouroboros_logo_icon_256.png'

        apprise_obj = apprise.Apprise(asset=asset)

        for notifier in self.config.notifiers:
            add = apprise_obj.add(notifier)
            if not add:
                self.logger.error(self._('Could not add notifier %s'), notifier)

        return apprise_obj

    def send(self, container_tuples=None, socket=None, kind='update', next_run=None, mode='container'):
        if kind == 'startup':
            title = self._('Ouroboros has started')
            body_fields = [
                self._('Host: %s') % self.config.hostname,
                self._('Time: %s') % dates.format_datetime(None, format='full', tzinfo=timezone(self.config.tz), locale=self.config.language),
                self._('Next Run: %s') % dates.format_datetime(next_run, format='full', tzinfo=timezone(self.config.tz), locale=self.config.language)]
        elif kind == 'monitor':
            title = self._('Ouroboros has detected updates!')
            body_fields = [
                self._('Host/Socket: %s / %s') % (self.config.hostname, socket.split('//')[1]),
                self._('Containers Monitored: %d') % self.data_manager.monitored_containers[socket],
                self._('Total Containers Updated: %d') % self.data_manager.total_updated[socket]
            ]
            body_fields.extend(
                [
                    self._("{} updated from {} to {}").format(
                        container.name,
                        old_image if mode == 'service' else old_image.short_id.split(':')[1],
                        new_image.short_id.split(':')[1]
                    ) for container, old_image, new_image in container_tuples
                ]
            )
        else:
            title = self._('Ouroboros has updated containers!')
            body_fields = [
                self._('Host/Socket: %s / %s') % (self.config.hostname, socket.split('//')[1]),
                self._('Containers Monitored: %d') % self.data_manager.monitored_containers[socket],
                self._('Total Containers Updated: %d') % self.data_manager.total_updated[socket],
                self._('Containers updated this pass: %d') % len(container_tuples)
            ]
            body_fields.extend(
                [
                    self._("{} updated from {} to {}").format(
                        container.name,
                        old_image if mode == 'service' else old_image.short_id.split(':')[1],
                        new_image.short_id.split(':')[1]
                    ) for container, old_image, new_image in container_tuples
                ]
            )
        body = '\r\n'.join(body_fields)

        if self.apprise.servers:
            self.apprise.notify(title=title, body=body, body_format=apprise.NotifyFormat.TEXT)
