from typing import Union, List

from mediawords.annotator import JSONAnnotator, McJSONAnnotatorException
from mediawords.util.config import get_config as py_get_config
from mediawords.util.log import create_logger
from mediawords.util.perl import decode_object_from_bytes_if_needed
from mediawords.util.web.user_agent import Request

log = create_logger(__name__)


class McCLIFFAnnotatorException(McJSONAnnotatorException):
    """CLIFF annotator exception."""
    pass


class CLIFFAnnotator(JSONAnnotator):
    """CLIFF annotator."""

    # CLIFF version tag set
    __CLIFF_VERSION_TAG_SET = 'geocoder_version'

    # CLIFF geographical names tag prefix
    __CLIFF_GEONAMES_TAG_PREFIX = 'geonames_'

    def annotator_is_enabled(self) -> bool:
        config = py_get_config()

        if config.get('cliff', {}).get('enabled', False):
            return True
        else:
            return False

    def _postgresql_raw_annotations_table(self) -> str:
        return 'cliff_annotations'

    def _request_for_text(self, text: str) -> Request:

        text = decode_object_from_bytes_if_needed(text)

        # CLIFF annotator URL
        config = py_get_config()
        url = config.get('cliff', {}).get('annotator_url', None)
        if url is None:
            raise McCLIFFAnnotatorException("Unable to determine CLIFF annotator URL to use.")

        request = Request(method='POST', url=url)
        request.set_content_type('application/x-www-form-urlencoded; charset=utf-8')
        request.set_content({'q': text})

        return request

    def _fetched_annotation_is_valid(self, annotation: Union[dict, list]) -> bool:

        annotation = decode_object_from_bytes_if_needed(annotation)

        if annotation is None:
            log.warning("Annotation is None.")
            return False

        if not isinstance(annotation, dict):
            log.warning("Annotation is not dict: %s" % str(annotation))
            return False

        if 'status' not in annotation:
            log.warning("Annotation doesn't have 'status' key: %s" % str(annotation))
            return False

        if annotation['status'] != 'ok':
            log.warning("Annotation's status is not 'ok': %s" % str(annotation))
            return False

        if 'results' not in annotation:
            log.warning("Annotation doesn't have 'results' key: %s" % str(annotation))
            return False

        if not isinstance(annotation['results'], dict):
            log.warning("Annotation's results is not dict: %s" % str(annotation))
            return False

        return True

    def _tags_for_annotation(self, annotation: Union[dict, list]) -> List[JSONAnnotator.Tag]:

        annotation = decode_object_from_bytes_if_needed(annotation)

        config = py_get_config()

        cliff_config = config.get('cliff', None)
        if cliff_config is None:
            raise McCLIFFAnnotatorException("CLIFF is not configured.")

        cliff_version_tag = cliff_config.get('cliff_version_tag', None)
        if cliff_version_tag is None:
            raise McCLIFFAnnotatorException("CLIFF version tag is unset in configuration.")

        cliff_geonames_tag_set = cliff_config.get('cliff_geonames_tag_set', None)
        if cliff_geonames_tag_set is None:
            raise McCLIFFAnnotatorException("CLIFF geographical names tag set is unset in configuration.")

        cliff_organizations_tag_set = cliff_config.get('cliff_organizations_tag_set', None)
        if cliff_organizations_tag_set is None:
            raise McCLIFFAnnotatorException("CLIFF organizations tag set is unset in configuration.")

        cliff_people_tag_set = cliff_config.get('cliff_people_tag_set', None)
        if cliff_people_tag_set is None:
            raise McCLIFFAnnotatorException("CLIFF people tag set is unset in configuration.")

        tags = list()

        tags.append(JSONAnnotator.Tag(tag_sets_name=self.__CLIFF_VERSION_TAG_SET,
                                      tag_sets_label=self.__CLIFF_VERSION_TAG_SET,
                                      tag_sets_description='CLIFF version the story was tagged with',
                                      tags_name=cliff_version_tag,
                                      tags_label=cliff_version_tag,
                                      tags_description="Story was tagged with '%s'" % cliff_version_tag))

        results = annotation.get('results', None)
        if results is None or len(results) == 0:
            return tags

        organizations = results.get('organizations', None)
        if organizations is not None:
            for organization in organizations:
                tags.append(JSONAnnotator.Tag(tag_sets_name=cliff_organizations_tag_set,
                                              tag_sets_label=cliff_organizations_tag_set,
                                              tag_sets_description='CLIFF organizations',

                                              # e.g. "United Nations"
                                              tags_name=organization['name'],
                                              tags_label=organization['name'],
                                              tags_description=organization['name']))

        people = results.get('people', None)
        if people is not None:
            for person in people:
                tags.append(JSONAnnotator.Tag(tag_sets_name=cliff_people_tag_set,
                                              tag_sets_label=cliff_people_tag_set,
                                              tag_sets_description='CLIFF people',

                                              # e.g. "Einstein"
                                              tags_name=person['name'],
                                              tags_label=person['name'],
                                              tags_description=person['name']))

        places = results.get('places', None)
        if places is not None:
            focus = places.get('focus', None)
            if focus is not None:

                countries = focus.get('countries', None)
                if countries is not None:

                    for country in countries:
                        tags.append(JSONAnnotator.Tag(tag_sets_name=cliff_geonames_tag_set,
                                                      tag_sets_label=cliff_geonames_tag_set,
                                                      tag_sets_description='CLIFF geographical names',

                                                      # e.g. "geonames_6252001"
                                                      tags_name=self.__CLIFF_GEONAMES_TAG_PREFIX + str(country['id']),

                                                      # e.g. "United States"
                                                      tags_label=country['name'],

                                                      # e.g. "United States | A | US"
                                                      tags_description='%(name)s | %(feature)s | %(country)s' % {
                                                          'name': country['name'],
                                                          'feature': country['featureClass'],
                                                          'country': country['countryCode'],
                                                      }))

                states = focus.get('states', None)
                if states is not None:

                    for state in states:
                        tags.append(JSONAnnotator.Tag(tag_sets_name=cliff_geonames_tag_set,
                                                      tag_sets_label=cliff_geonames_tag_set,
                                                      tag_sets_description='CLIFF geographical names',

                                                      # e.g. "geonames_4273857"
                                                      tags_name=self.__CLIFF_GEONAMES_TAG_PREFIX + str(state['id']),

                                                      # e.g. "Kansas"
                                                      tags_label=state['name'],

                                                      # e.g. "Kansas | A | KS | US"
                                                      tags_description=(
                                                                           '%(name)s | %(feature)s | '
                                                                           '%(state)s | %(country)s'
                                                                       ) % {
                                                                           'name': state['name'],
                                                                           'feature': state['featureClass'],
                                                                           'state': state['stateCode'],
                                                                           'country': state['countryCode'],
                                                                       }))

                cities = focus.get('cities', None)
                if cities is not None:

                    for city in cities:
                        tags.append(JSONAnnotator.Tag(tag_sets_name=cliff_geonames_tag_set,
                                                      tag_sets_label=cliff_geonames_tag_set,
                                                      tag_sets_description='CLIFF geographical names',

                                                      # e.g. "geonames_4273857"
                                                      tags_name=self.__CLIFF_GEONAMES_TAG_PREFIX + str(city['id']),

                                                      # e.g. "Kansas"
                                                      tags_label=city['name'],

                                                      # e.g. "Kansas | A | KS | US"
                                                      tags_description=(
                                                                           '%(name)s | %(feature)s | '
                                                                           '%(state)s | %(country)s'
                                                                       ) % {
                                                                           'name': city['name'],
                                                                           'feature': city['featureClass'],
                                                                           'state': city['stateCode'],
                                                                           'country': city['countryCode'],
                                                                       }))

        return tags
