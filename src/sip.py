from .config import SIP_PORT, RTP_PORT, BIND_IP, SDP_IP

def get_header(req, name):
    for l in req.split("\r\n"):
        if l.lower().startswith(name.lower()+":"): 
            return l.split(":",1)[1].strip()
    return ""

def parse_port(req, default):
    try:
         if "\r\n\r\n" in req:
             body = req.split("\r\n\r\n")[1]
             for l in body.split("\r\n"):
                 if l.startswith("m=audio"): 
                     return int(l.split(" ")[1])
    except: pass
    return default

def create_response(code, txt, req, to_tag=None, sdp=False):
    via = get_header(req, 'Via')
    from_hdr = get_header(req, 'From')
    to_hdr = get_header(req, 'To')
    call_id = get_header(req, 'Call-ID')
    cseq = get_header(req, 'CSeq')
    
    if to_tag and 'tag=' not in to_hdr:
        to_hdr += f";tag={to_tag}"
        
    s = ""
    if sdp: 
        s = f"v=0\r\no=- 1 1 IN IP4 {SDP_IP}\r\ns=Py\r\nc=IN IP4 {SDP_IP}\r\nt=0 0\r\nm=audio {RTP_PORT} RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\na=sendrecv\r\n"

        
    return (f"SIP/2.0 {code} {txt}\r\n"
            f"Via: {via}\r\n"
            f"From: {from_hdr}\r\n"
            f"To: {to_hdr}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq}\r\n"
            f"Contact: <sip:{BIND_IP}:{SIP_PORT}>\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(s)}\r\n\r\n{s}").encode()

def create_refer(caller_id, target_ip, call_id, operator_ext):
    # This is a simplified REFER, might need more headers depending on Yeastar config
    msg = (f"REFER sip:{caller_id}@{target_ip} SIP/2.0\r\n"
           f"Via: SIP/2.0/UDP {BIND_IP}:{SIP_PORT};branch=z9hG4bK_refer\r\n"
           f"From: <sip:ai@{BIND_IP}>;tag=srv\r\n"
           f"To: <sip:{caller_id}@{target_ip}>\r\n"
           f"Call-ID: {call_id}\r\n"
           f"CSeq: 102 REFER\r\n"
           f"Contact: <sip:ai@{BIND_IP}:{SIP_PORT}>\r\n"
           f"Refer-To: <sip:{operator_ext}@{target_ip}>\r\n"
           f"Content-Length: 0\r\n\r\n")
    return msg.encode()

def create_bye(caller_id, target_ip, call_id):
    msg = (f"BYE sip:{caller_id}@{target_ip} SIP/2.0\r\n"
           f"Via: SIP/2.0/UDP {BIND_IP}:{SIP_PORT};branch=z9hG4bK_bye\r\n"
           f"From: <sip:ai@{BIND_IP}>;tag=srv\r\n"
           f"To: <sip:{caller_id}@{target_ip}>\r\n"
           f"Call-ID: {call_id}\r\n"
           f"CSeq: 103 BYE\r\n"
           f"Content-Length: 0\r\n\r\n")
    return msg.encode()
