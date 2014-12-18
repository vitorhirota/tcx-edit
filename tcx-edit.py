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
    hrm = map(int, track.xpath('.//ts:HeartRateBpm/ts:Value/text()', namespaces=ns))
    speed = map(float, track.xpath('//g:Speed/text()', namespaces=ns))
    elements = ['./ts:TotalTimeSeconds',
                './ts:DistanceMeters',
                './ts:MaximumSpeed',
                './ts:Calories',
                './ts:AverageHeartRateBpm/ts:Value',
                './ts:MaximumHeartRateBpm/ts:Value',
                './/g:AvgSpeed']
    values = [len(track) - 1,
              __calculate_distance(),
              max(speed),
              lap.find('./ts:Calories', namespaces=ns).text, # replicate calories info
              sum(hrm)//len(hrm),
              max(hrm),
              sum(speed)/len(speed)]
    for e, v in zip(elements, values):
        lap.find(e, namespaces=ns).text = str(v)

def split_at(tcx, arguments):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(tcx, parser)
    root = tree.getroot()
    activity = root.xpath('./ts:Activities/ts:Activity', namespaces=ns)[0]
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
    pass

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
