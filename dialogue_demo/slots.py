"""Intent-driven human-friendly slots with single/multi-slot clarification support.
An explicit `key=value; key=value` reply is deterministic; free-text answers
fill the *current* question plus clearly recognizable categorical slots only.
"""
import re

SLOT_SPECS = {
 'music': {
  'artist': {'song_title':'What is the song title?', 'performer_role':'Whose name do you want: lead singer, band, or composer?', 'recording_version':'Which version: original, live, or cover?'},
  'release_year': {'work_title':'What is the song or album title?', 'work_type':'Is it a song or an album?', 'release_edition':'Do you mean the first release or a remastered/reissued edition?'},
  'album': {'song_title':'Which song is it?', 'performer_name':'Who performs it (artist or band name)?', 'recording_version':'Which version: original, live, or cover?'},
  'genre': {'work_title':'Which song or album is it?', 'work_type':'Is this a song or an album?', 'genre_scope':'Would you like the main genre or a specific subgenre?'},
 },
 'art': {
  'creator': {'artwork_title':'What is the artwork title?', 'medium':'Is it a painting, sculpture, or photograph?', 'creator_role':'Do you mean the individual artist or a workshop/collective?'},
  'creation_year': {'artwork_title':'What is the artwork title?', 'medium':'Is it a painting, sculpture, or photograph?', 'date_type':'Do you want the year it was started or finished?'},
  'movement': {'artwork_title':'Which artwork do you mean?', 'medium':'Is it a painting, sculpture, or photograph?', 'genre_scope':'Do you want the broad movement or a specific artistic style?'},
  'location': {'artwork_title':'What is the artwork title?', 'medium':'Is it a painting, sculpture, or photograph?', 'location_type':'Do you want its current museum or original location?'},
 }
}
SLOT_LABELS = {
 'song_title':'Song title', 'work_title':'Song / album title', 'artwork_title':'Artwork title',
 'performer_role':'Singer / band / composer', 'recording_version':'Recording version',
 'release_edition':'First release / reissue', 'performer_name':'Performing artist / band',
 'work_type':'Song or album', 'genre_scope':'Main genre / detailed style',
 'medium':'Type of artwork', 'creator_role':'Artist or workshop',
 'date_type':'Started or finished', 'location_type':'Current museum / original location'
}
SLOT_EXAMPLES = {'song_title':'Bohemian Rhapsody','work_title':'Thriller','artwork_title':'Mona Lisa',
 'performer_role':'lead singer','recording_version':'original','release_edition':'first release',
 'performer_name':'Queen','work_type':'album','genre_scope':'main genre',
 'medium':'painting','creator_role':'individual artist','date_type':'finished',
 'location_type':'current museum'}
CHOICES = {
 'performer_role': {'lead singer':'lead singer','singer':'lead singer','vocalist':'lead singer', 'band':'band','group':'band','performing group':'band','composer':'composer'},
 'recording_version': {'original':'original','studio':'original','live':'live','cover':'cover'},
 'release_edition': {'first':'first release','first release':'first release','original':'first release','reissue':'reissue','remaster':'reissue','remastered':'reissue','reissued':'reissue'},
 'work_type': {'song':'song','single':'song','track':'song','album':'album'},
 'genre_scope': {'main':'main genre','genre':'main genre','main genre':'main genre','broad':'main genre','movement':'main genre','specific':'specific style','subgenre':'specific style','style':'specific style','detailed':'specific style','specific style':'specific style'},
 'medium': {'painting':'painting','painted':'painting','sculpture':'sculpture','sculpted':'sculpture','photograph':'photograph','photography':'photograph','photo':'photograph'},
 'creator_role': {'artist':'individual artist','individual':'individual artist','individual artist':'individual artist','workshop':'workshop','collective':'workshop'},
 'date_type': {'started':'started','start':'started','finished':'finished','completed':'finished','finish':'finished'},
 'location_type': {'current':'current museum','current museum':'current museum','museum':'current museum','original':'original location','original location':'original location'}
}
PATTERNS = {
 ('music','artist'):[r'who (?:sings|sang|performed|composed) (.+)',r'who is the (?:singer|artist|musician) (?:of|behind) (.+)'],
 ('music','release_year'):[r'when was (.+) released',r'what year did (.+) come out',r'what is the release date of (.+)',r'when did (.+) come out'],
 ('music','album'):[r'which album (?:includes|contains|features) (.+)',r'what album is (.+) on',r'which record contains (.+)',r'name the album featuring (.+)'],
 ('music','genre'):[r'what genre is (.+)',r'what is the (?:musical style|genre) of (.+)',r'what music genre does (.+) belong to'],
 ('art','creator'):[r'who (?:painted|created|made|sculpted) (.+)',r'who is the (?:artist|creator) (?:of|behind) (.+)'],
 ('art','creation_year'):[r'when was (.+) (?:painted|created|made)',r'what year was (.+) (?:painted|created|made)',r'what is the creation date of (.+)'],
 ('art','movement'):[r'what art movement is (.+)',r'what artistic style is (.+)',r'which movement does (.+) belong to'],
 ('art','location'):[r'where is (.+) (?:displayed|kept|located)',r'which museum houses (.+)',r'where can i see (.+)',r'what museum keeps (.+)']
}
LEADING = re.compile(r'^(?:the name of |the song |the album |the artwork |the painting |the sculpture )',re.I)

def validate_slot(slot, value):
 value=re.sub(r'\s+',' ',str(value)).strip().strip('?!.,; ')
 if not value or len(value)>160 or value.casefold() in {'none','unknown','not sure','i do not know','?','it','this','that'}:return None
 if slot in CHOICES:return CHOICES[slot].get(value.casefold())
 if value.casefold() in {'the song','the artwork','the album'}:return None
 return value

def extract_slots(topic,intent,text):
 result={}; spec=SLOT_SPECS[topic][intent]
 title_key='song_title' if 'song_title' in spec else 'work_title' if 'work_title' in spec else 'artwork_title'
 for pattern in PATTERNS.get((topic,intent),[]):
  match=re.fullmatch(pattern,text.strip().rstrip('?!.'),flags=re.I)
  if match:
   val=validate_slot(title_key,LEADING.sub('',match.group(1).strip()))
   if val:result[title_key]=val
   break
 # Only infer defaults from explicit wording. Do not fabricate three slot answers.
 if "performer_role" in spec and re.search(r"\b(?:sings|sang|vocalist)\b",text,re.I):result["performer_role"]="lead singer"
 if "medium" in spec and re.search(r"\b(?:painted|painting)\b",text,re.I):result["medium"]="painting"
 if "medium" in spec and re.search(r"\b(?:sculpted|sculpture)\b",text,re.I):result["medium"]="sculpture"
 for slot in spec:
  if slot in CHOICES:
   # Word-boundary scan, longest variants first.
   values=[]
   for alias, canonical in sorted(CHOICES[slot].items(),key=lambda x:-len(x[0])):
    if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text,re.I):values.append(canonical)
   values=list(dict.fromkeys(values))
   if len(values)==1:result[slot]=values[0]
 return result

def missing_slots(topic,intent,slots):return [s for s in SLOT_SPECS[topic][intent] if not slots.get(s)]
def slot_question(topic,intent,slot):return SLOT_SPECS[topic][intent][slot]

def parse_clarification(topic,intent,reply,missing):
 """Return (accepted mapping, rejected entries, input mode). Never overwrite filled slots."""
 spec=SLOT_SPECS[topic][intent]; reply=reply.strip()
 if not reply:return {},[], 'empty'
 accepted={};rejected=[]
 # Deterministic, flexible bulk reply. key=value ; key=value supports one or all.
 fields=re.findall(r'(?:^|;)\s*([a-z_]+)\s*[:=]\s*([^;]+)',reply,flags=re.I)
 if fields:
  for raw_key,value in fields:
   key=raw_key.casefold().strip()
   if key not in spec or key not in missing:rejected.append({'field':key,'value':value,'reason':'not an outstanding slot'});continue
   validated=validate_slot(key,value)
   if validated:accepted[key]=validated
   else:rejected.append({'field':key,'value':value,'reason':'invalid value or option'})
  return accepted,rejected,'labeled-multi'
 # Unlabeled answers: fill only the currently asked free-text slot, plus
 # unique, explicit choice mentions for *other* missing slots.
 current=missing[0]; matched_choices={}
 for key in missing:
  if key not in CHOICES:continue
  values=[]
  for alias,canonical in sorted(CHOICES[key].items(),key=lambda x:-len(x[0])):
   if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',reply,re.I):values.append(canonical)
  values=list(dict.fromkeys(values))
  if len(values)==1:matched_choices[key]=values[0]
 if current in CHOICES:
  if current in matched_choices:accepted[current]=matched_choices[current]
 elif current in ('song_title','artwork_title','work_title','performer_name'):
  # If the user gives a free text title, use it as current slot only.
  # Bare text is not split into guesses about any other named entities.
  title=reply
  for value in matched_choices.values():
   title=re.sub(r'(?i)\b'+re.escape(value)+r'\b','',title).strip(' ,;')
  validated=validate_slot(current,title)
  if validated:accepted[current]=validated
 accepted.update({key:v for key,v in matched_choices.items() if key in missing})
 return accepted,rejected,'natural'
