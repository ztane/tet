# -*- coding: utf-8 -*-
from __future__ import absolute_import, division,\
       print_function, unicode_literals

from pyramid.decorator import reify
import venusian
import re
from zope.interface import Interface

_to_underscores = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def _underscore(name):
    return _to_underscores.sub(r'_\1', name).lower()


_is_iface_name = re.compile('^I[A-Z].*')


class ServiceRegistry(object):
    def __init__(self):
        self.__services__ = []

    def _register_service(self, instance, interface):
        self.__services__.append((instance, interface))
        name = interface.__name__
        if _is_iface_name.match(name):
            name = name[1:]

        setattr(self, _underscore(name), instance)


def get_service_registry(registry):
    if not hasattr(registry, 'services'):
        registry.services = ServiceRegistry()

    return registry.services


def service(interface=Interface, name='', context_iface=Interface, scope='global'):
    if scope not in ['global', 'request']:
        raise ValueError("Invalid scope %s, must be either 'global' or 'request'" % (scope,))

    service_name = name
    def service_decorator(wrapped):
        def callback(scanner, name, ob):
            registry = scanner.config.registry

            if scope == 'global':
                print(ob, scanner, name)
                # register only once
                if not isinstance(registry.queryUtility(interface), ob):
                    print(ob)
                    ob_instance = ob(registry=registry)
                    get_service_registry(registry)._register_service(ob_instance, interface)
                    registry.registerUtility(ob_instance, interface)
                    scanner.config.register_service(ob_instance, interface, Interface, service_name)

            else:
                # noinspection PyUnusedLocal
                def service_factory(context, request):
                    return ob(request=request)

                scanner.config.register_service_factory(
                    service_factory, interface, context_iface, name=service_name)

        info = venusian.attach(wrapped, callback, category='tet.service')
        return wrapped

    return service_decorator


def autowired(interface=Interface, name=''):
    @reify
    def getter(self):
        if hasattr(self, 'request'):
            context = getattr(self.request, 'context', None)
            return self.request.find_service(interface, context, name)

        return self.registry.getUtility(interface, name)

    return getter


class BaseService(object):
    def __init__(self, **kw):
        try:
            self.registry = kw.pop('registry')
            super(BaseService, self).__init__(**kw)

        except KeyError:
            raise TypeError("Registry to the base business must be provided")


class RequestScopedBaseService(object):
    def __init__(self, **kw):
        try:
            self.request = kw.pop('request')
            super(RequestScopedBaseService, self).__init__(**kw)

        except KeyError:
            raise TypeError("Request to the base business must be provided")


def scan_services(config, *a, **kw):
    kw['categories'] = ('tet.service',)
    return config.scan(*a, **kw)


def includeme(config):
    config.add_directive('scan_services', scan_services)
    config.registry.services = ServiceRegistry()