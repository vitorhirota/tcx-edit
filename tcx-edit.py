from lxml import etree

import argparse
import copy
import operator
import sys

# namespaces
ns = {
    'ts': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
    'g': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2',
}

def _update_lap_info(lap):
    def __calculate_distance():
        prev = lap
        distances = []
        for i in range(2):
            try:
                distances.append(float(prev.xpath('.//ts:DistanceMeters[last()]', namespaces=ns)[0].text))
                prev = prev.getprevious()
            except:
                break
        return reduce(operator.sub, distances)
    track = lap.find('./Track', namespaces=ns)
    lap.set('StartTime', track[0].find('./ts:Time', namespaces=ns).text)
    totaltime = len(track) - 1,
    distance = __calculate_distance()
    hrm = map(int, track.xpath('.//ts:HeartRateBpm/ts:Value/text()', namespaces=ns))
    speed = map(float, track.xpath('//g:Speed/text()', namespaces=ns))
    elements = ['./ts:TotalTimeSeconds',
                './ts:DistanceMeters',
                './ts:MaximumSpeed',
                './ts:Calories',
                './ts:AverageHeartRateBpm/ts:Value',
                './ts:MaximumHeartRateBpm/ts:Value',
                './/g:AvgSpeed']
    values = [totaltime,
              distance,
              max(speed),
              lap.find('./ts:Calories', namespaces=ns).text, # replicate calories info
              sum(hrm)//len(hrm),
              max(hrm),
              distance/totaltime]
    for e, v in zip(elements, values):
        lap.find(e, namespaces=ns).text = str(v)

def split_at(tcx, arguments):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(tcx, parser)
    root = tree.getroot()
    for i in arguments:
        try:
            hh, mm, ss = map(int, i.split(':'))
            index = hh*(60**2) + mm*(60**1) + ss
            # index = sum([int(i)*(60**idx) for idx, i in enumerate(reversed(i.split(':')))])
        except:
            print 'ERROR: split_at arguments should be in HH:MM:SS format.'
            print 'Failed argument: %s' % i
        # find split trackpoint
        tp = root.xpath('//ts:Trackpoint[%s]' % index, namespaces=ns)[0]
        track = tp.getparent()
        trackpoints = [
            track.xpath('./ts:Trackpoint[position()<=%s]' % track.index(tp), namespaces=ns),
            track.xpath('./ts:Trackpoint[position()>%s]' % track.index(tp), namespaces=ns)
        ]
        # edit/copy laps
        lap = track.getparent()
        lap.remove(track)
        lap2 = copy.deepcopy(lap)
        lap.addnext(lap2)
        # fix lap info
        for _lap, _ts in zip([lap, lap2], trackpoints):
            _track = _lap.makeelement('Track')
            _lap.append(_track)
            for t in _ts:
                _track.append(t)
            # copy extension
            _track.append(copy.deepcopy(track[-1]))
            # update lap info
            _update_lap_info(_lap)
    # save xml
    new_tcx = tcx.replace('.tcx', '-edit.tcx')
    tree.write(new_tcx, pretty_print=True, encoding="UTF-8", xml_declaration=True)
    print 'Done!'


def merge(tcx, arguments):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(tcx, parser)
    root = tree.getroot()
    laps = root.findall('.//ts:Lap', namespaces=ns)
    for i in arguments:
        try:
            begin, end = map(int, i.split('-'))
        except:
            print 'ERROR: merge arguments should be in n1-n2 format, where n1',
            print 'is the begining lap index and n2 is the end lap index to be',
            print 'merge.'
            print 'Failed argument: %s' % i
        _laps_list = laps[slice(begin-1, end)]
        mergedlap = _laps_list[0]
        track = mergedlap.find('./ts:Track', namespaces=ns)
        # merge trackpoints
        _laps_elm = etree.Element('laps')
        for l in _laps_list:
            # build a element with laps list to use xpath statements
            _laps_elm.append(copy.deepcopy(l))
            for t in l.findall('.//ts:Trackpoint', namespaces=ns):
                track.append(t)
        # move avg speed to the end
        track.append(track.find('./ts:Extensions', namespaces=ns))
        # update lap info
        elements = ['./ts:TotalTimeSeconds',
                    './ts:DistanceMeters',
                    './ts:MaximumSpeed',
                    './ts:Calories',
                    './ts:AverageHeartRateBpm/ts:Value',
                    './ts:MaximumHeartRateBpm/ts:Value',
                    './/g:AvgSpeed']
        speed = map(float, _laps_elm.xpath('.//g:Speed/text()', namespaces=ns))
        hrm = map(int, _laps_elm.xpath('.//ts:HeartRateBpm//ts:Value/text()', namespaces=ns))
        totaltime = int(_laps_elm.xpath('count(.//ts:Trackpoint)', namespaces=ns))
        distance = float(_laps_elm.xpath('sum(./*/ts:DistanceMeters/text())', namespaces=ns))
        values = [totaltime,
                  distance,
                  max(speed),
                  int(_laps_elm.xpath('sum(.//ts:Calories/text())', namespaces=ns)),
                  sum(hrm)/len(hrm),
                  max(hrm),
                  distance/totaltime]
        for e, v in zip(elements, values):
            mergedlap.find(e, namespaces=ns).text = str(v)
        # remove laps
        activity = root.find('./*/ts:Activity', namespaces=ns)
        for l in _laps_list[1:]:
            activity.remove(l)
    # save xml
    new_tcx = tcx.replace('.tcx', '-edit.tcx')
    tree.write(new_tcx, pretty_print=True, encoding="UTF-8", xml_declaration=True)
    print 'Done!'

parser = argparse.ArgumentParser(description='Edit TCX files.')
parser.add_argument('tcx_file', help='what file to edit')
parser.add_argument('action', choices=['split_at', 'merge'],
                    help='which action to take')
parser.add_argument('arguments', nargs='+',
                   help='arguments for the given action')
# parser.add_argument('-out',
#                    help='output file name')

args = parser.parse_args(sys.argv[1:])

print '## TCX Edit ##'
print '%s: %s with %s arguments' % (args.tcx_file,
                                    args.action,
                                    args.arguments)
fn = globals()[args.action]
fn(args.tcx_file, args.arguments)



# tcx structure
# <TrainingCenterDatabase
#     [..]
#     xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
#     [..]
#     xmlns:ns2="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
#     <Activities>
#         <Activity Sport="Biking">
#             <Id>2014-12-17T08:36:27.000Z</Id>
#             <Lap StartTime="2014-12-17T08:36:27.000Z">
#                 <TotalTimeSeconds>5031</TotalTimeSeconds>
#                 <DistanceMeters>39548.2</DistanceMeters>
#                 <MaximumSpeed>15.4216</MaximumSpeed>
#                 <Calories>1288</Calories>
#                 <AverageHeartRateBpm>
#                     <Value>144</Value>
#                 </AverageHeartRateBpm>
#                 <MaximumHeartRateBpm>
#                     <Value>168</Value>
#                 </MaximumHeartRateBpm>
#                 <Intensity>Active</Intensity>
#                 <TriggerMethod>Manual</TriggerMethod>
#                 <Track>
#                     <Trackpoint>
#                         <Time>2014-12-17T08:36:27.000Z</Time>
#                         <Position>
#                             <LatitudeDegrees>-22.9052200</LatitudeDegrees>
#                             <LongitudeDegrees>-47.0510990</LongitudeDegrees>
#                         </Position>
#                         <AltitudeMeters>691</AltitudeMeters>
#                         <HeartRateBpm>
#                             <Value>105</Value>
#                         </HeartRateBpm>
#                         <Extensions>
#                             <TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
#                                 <Speed>6.41176</Speed>
#                             </TPX>
#                         </Extensions>
#                     </Trackpoint>
#                     [..]
#                     <Extensions>
#                         <LX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
#                             <AvgSpeed>7.67024</AvgSpeed>
#                         </LX>
#                     </Extensions>
#                 </Track>
#             </Lap>
#             <Creator xsi:type="Device_t">
#                 <Name>TomTom GPS Sport Watch</Name>
#                 <UnitId>0</UnitId>
#                 <ProductID>0</ProductID>
#                 <Version>
#                     <VersionMajor>1</VersionMajor>
#                     <VersionMinor>8</VersionMinor>
#                     <BuildMajor>25</BuildMajor>
#                     <BuildMinor>0</BuildMinor>
#                 </Version>
#             </Creator>
#         </Activity>
#     </Activities>
# </TrainingCenterDatabase>
