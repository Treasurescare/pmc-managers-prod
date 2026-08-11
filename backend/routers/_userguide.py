"""User-journey flowchart — a NEW "How to use PMC Managers v2" flowchart
covering the actual actions a Vendor, Admin, Staff (Escrow/Certifier/Legal/
Accounting/Committee) will take from account creation to signed contract.

Companion to the platform-architecture flowchart (`_flowchart.py`). This one
is deliberately step-by-step and light on internal jargon — it's meant for
onboarding new users and for showing customers "how do I do X".
"""


def build_user_guide_svg() -> str:
    return """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 1720'
     width='1600' height='1720' preserveAspectRatio='xMidYMid meet'
     font-family='Calibri, Arial, sans-serif' font-size='14'>
  <defs>
    <marker id='ug-arrow' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='10' markerHeight='10' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#0b1f3a'/>
    </marker>
    <marker id='ug-arrow-vendor' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='10' markerHeight='10' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#065f46'/>
    </marker>
    <marker id='ug-arrow-admin' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='10' markerHeight='10' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#6b21a8'/>
    </marker>
    <style>
      .box     { fill: #ffffff; stroke: #0b1f3a; stroke-width: 1.5; rx: 8; }
      .box-v   { fill: #d1fae5; stroke: #065f46; stroke-width: 1.5; }
      .box-a   { fill: #ede9fe; stroke: #6b21a8; stroke-width: 1.5; }
      .box-s   { fill: #fef3c7; stroke: #92400e; stroke-width: 1.5; }
      .box-hi  { fill: #0b1f3a; stroke: #0b1f3a; }
      .box-hi text { fill: #ffffff; }
      .title   { font-size: 14px; font-weight: 700; fill: #0b1f3a; }
      .num     { font-size: 11px; font-weight: 700; fill: #64748b; }
      .sub     { font-size: 11px; fill: #475569; }
      .step-num { font-size: 22px; font-weight: 800; fill: #cbd5e1; }
      .lane    { fill: #f8fafc; stroke: #e2e8f0; stroke-dasharray: 3 3; }
      .lane-title { font-size: 13px; font-weight: 700; fill: #64748b; letter-spacing: 1.5px; }
      .arrow-v { stroke: #065f46; stroke-width: 1.8; fill: none; }
      .arrow-a { stroke: #6b21a8; stroke-width: 1.8; fill: none; }
      .arrow   { stroke: #0b1f3a; stroke-width: 1.5; fill: none; }
      .legend text { font-size: 12px; fill: #334155; }
    </style>
  </defs>

  <!-- ============ Header ============ -->
  <text x='40' y='38' class='title' font-size='24' fill='#0b1f3a'>PMC Managers v2 — How to use the platform</text>
  <text x='40' y='60' class='sub' font-size='12'>Step-by-step user journey · from account creation to a signed contract · Vendor · Admin · Staff</text>

  <!-- ============ Legend ============ -->
  <g class='legend' transform='translate(40, 76)'>
    <rect x='0'   y='0' width='16' height='12' class='box-v'/>    <text x='22' y='10'>Vendor action</text>
    <rect x='140' y='0' width='16' height='12' class='box-a'/>    <text x='162' y='10'>Admin action</text>
    <rect x='280' y='0' width='16' height='12' class='box-s'/>    <text x='302' y='10'>Staff action (Escrow/Legal/Acct/Cert)</text>
    <rect x='560' y='0' width='16' height='12' class='box-hi'/>   <text x='582' y='10'>System-generated event</text>
  </g>

  <!-- ============ Swim lanes ============ -->
  <rect class='lane' x='30'   y='108' width='1550' height='260'/>
  <text x='45' y='128' class='lane-title'>PHASE 1 · ONBOARD</text>

  <rect class='lane' x='30'   y='378' width='1550' height='300'/>
  <text x='45' y='398' class='lane-title'>PHASE 2 · PUBLISH TENDER &amp; INVITE BIDS</text>

  <rect class='lane' x='30'   y='688' width='1550' height='340'/>
  <text x='45' y='708' class='lane-title'>PHASE 3 · VENDOR BIDS &amp; PAYS EMD</text>

  <rect class='lane' x='30'   y='1038' width='1550' height='300'/>
  <text x='45' y='1058' class='lane-title'>PHASE 4 · APPROVAL PIPELINE &amp; AWARD</text>

  <rect class='lane' x='30'   y='1348' width='1550' height='320'/>
  <text x='45' y='1368' class='lane-title'>PHASE 5 · CONTRACT · SIGN · SETTLE</text>

  <!-- ============ PHASE 1: ONBOARD ============ -->
  <text x='55' y='170' class='step-num'>1</text>
  <g transform='translate(90,150)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Admin logs in</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>/admin/login</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>adminsupport@pmcmanagers.com</text>
  </g>
  <text x='390' y='170' class='step-num'>2</text>
  <g transform='translate(420,150)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Configure Product Catalog</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Admin Dashboard → Product Catalog</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Set prices · currencies · UNSPSC tags</text>
  </g>
  <text x='720' y='170' class='step-num'>3</text>
  <g transform='translate(750,150)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Set up Staff accounts</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Admin Dashboard → Permissions</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Assign roles: Escrow · Legal · etc.</text>
  </g>
  <text x='1050' y='170' class='step-num'>4</text>
  <g transform='translate(1080,150)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Vendor self-registers</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>/register  (Sections A–E)</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Or admin invites via email token</text>
  </g>

  <text x='55' y='300' class='step-num'>5</text>
  <g transform='translate(90,280)'>
    <rect class='box-v' width='260' height='80' rx='8'/>
    <text x='130' y='28' text-anchor='middle' class='title'>Upload KYC docs</text>
    <text x='130' y='48' text-anchor='middle' class='sub'>Articles · bank ref · POA</text>
    <text x='130' y='66' text-anchor='middle' class='sub'>Section C document slots</text>
  </g>
  <text x='390' y='300' class='step-num'>6</text>
  <g transform='translate(420,280)'>
    <rect class='box-s' width='260' height='80' rx='8'/>
    <text x='130' y='28' text-anchor='middle' class='title'>Legal reviews KYC</text>
    <text x='130' y='48' text-anchor='middle' class='sub'>/staff/login as Legal</text>
    <text x='130' y='66' text-anchor='middle' class='sub'>Approve / reject / request more</text>
  </g>
  <text x='720' y='300' class='step-num'>7</text>
  <g transform='translate(750,280)'>
    <rect class='box-hi' width='260' height='80' rx='8'/>
    <text x='130' y='28' text-anchor='middle' class='title'>KYC status = Verified</text>
    <text x='130' y='48' text-anchor='middle' class='sub'>Vendor unlocked to bid</text>
    <text x='130' y='66' text-anchor='middle' class='sub'>Otherwise HTTP 412 on submit</text>
  </g>
  <path class='arrow' d='M350 195 L420 195' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 195 L750 195' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M1010 195 L1080 195' marker-end='url(#ug-arrow)'/>
  <path class='arrow-v' d='M1210 240 Q1210 260, 220 280' marker-end='url(#ug-arrow-vendor)'/>
  <path class='arrow' d='M350 320 L420 320' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 320 L750 320' marker-end='url(#ug-arrow)'/>

  <!-- ============ PHASE 2: PUBLISH TENDER ============ -->
  <text x='55' y='440' class='step-num'>8</text>
  <g transform='translate(90,420)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Draft tender</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Admin → Tender Builder</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Clone master · edit sections A–R</text>
  </g>
  <text x='390' y='440' class='step-num'>9</text>
  <g transform='translate(420,420)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Attach BOQ + docs</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Upload Excel BOQ · PDFs</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Tag UNSPSC commodity</text>
  </g>
  <text x='720' y='440' class='step-num'>10</text>
  <g transform='translate(750,420)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Publish notice</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Admin → Notices → Publish</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Sets deadline · locks approval matrix</text>
  </g>
  <text x='1050' y='440' class='step-num'>11</text>
  <g transform='translate(1080,420)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Live on Public Board</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>/notices  (no login)</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Vendors download docs · EN/RU/KK</text>
  </g>

  <text x='55' y='570' class='step-num'>12</text>
  <g transform='translate(90,550)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Publish corrigenda (optional)</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Extend deadline · amend clauses</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Auto-notifies subscribed vendors</text>
  </g>
  <text x='390' y='570' class='step-num'>13</text>
  <g transform='translate(420,550)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Vendor asks a clarification</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Public Q&amp;A thread</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Email masked · admin replies</text>
  </g>
  <text x='720' y='570' class='step-num'>14</text>
  <g transform='translate(750,550)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Schedule pre-bid meeting</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Admin → Meetings</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Jitsi (free) or Zoom (S2S OAuth)</text>
  </g>
  <path class='arrow' d='M350 465 L420 465' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 465 L750 465' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M1010 465 L1080 465' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M350 595 L420 595' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 595 L750 595' marker-end='url(#ug-arrow)'/>

  <!-- ============ PHASE 3: VENDOR BIDS + EMD ============ -->
  <text x='55' y='750' class='step-num'>15</text>
  <g transform='translate(90,730)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Vendor logs in</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>/vendor/login</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Sees active notices dashboard</text>
  </g>
  <text x='390' y='750' class='step-num'>16</text>
  <g transform='translate(420,730)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Fill technical + commercial bid</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Two-cover envelope</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Price + tech notes + docs</text>
  </g>
  <text x='720' y='750' class='step-num'>17</text>
  <g transform='translate(750,730)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Pick payment rail</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Stripe · PayPal · Kaspi</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>EMD amount from notice</text>
  </g>
  <text x='1050' y='750' class='step-num'>18</text>
  <g transform='translate(1080,730)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>EMD received</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Escrow ledger row = received</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Bid becomes visible to committee</text>
  </g>

  <text x='55' y='890' class='step-num'>19</text>
  <g transform='translate(90,870)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Vendor reviews bids</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>My Bids dashboard</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Withdraw before deadline</text>
  </g>
  <text x='390' y='890' class='step-num'>20</text>
  <g transform='translate(420,870)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Attend reverse auction (opt)</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Live bid room</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Anti-snipe · anonymised</text>
  </g>
  <text x='720' y='890' class='step-num'>21</text>
  <g transform='translate(750,870)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Deadline hits</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Cover 1 (tech) auto-opens</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Cover 2 stays sealed until clear</text>
  </g>
  <path class='arrow-v' d='M350 775 L420 775' marker-end='url(#ug-arrow-vendor)'/>
  <path class='arrow-v' d='M680 775 L750 775' marker-end='url(#ug-arrow-vendor)'/>
  <path class='arrow-v' d='M1010 775 L1080 775' marker-end='url(#ug-arrow-vendor)'/>
  <path class='arrow-v' d='M350 915 L420 915' marker-end='url(#ug-arrow-vendor)'/>
  <path class='arrow-v' d='M680 915 L750 915' marker-end='url(#ug-arrow-vendor)'/>

  <!-- ============ PHASE 4: APPROVAL PIPELINE ============ -->
  <text x='55' y='1100' class='step-num'>22</text>
  <g transform='translate(90,1080)'>
    <rect class='box-s' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Certifier verifies bidder</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Site visit · references</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Sign off in staff console</text>
  </g>
  <text x='390' y='1100' class='step-num'>23</text>
  <g transform='translate(420,1080)'>
    <rect class='box-s' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Legal clears clauses</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Redline optional bid clauses</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>AI redline suggestion (advisory)</text>
  </g>
  <text x='720' y='1100' class='step-num'>24</text>
  <g transform='translate(750,1080)'>
    <rect class='box-s' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Accounting confirms EMD</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Ledger reconciles gateway</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Approves financial capacity</text>
  </g>
  <text x='1050' y='1100' class='step-num'>25</text>
  <g transform='translate(1080,1080)'>
    <rect class='box-s' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Committee scores bids</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Rubric per criterion</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>L1 auto-comparison helper</text>
  </g>

  <text x='55' y='1230' class='step-num'>26</text>
  <g transform='translate(90,1210)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Cover 2 opens</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Financial cover revealed</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Only for tech-clear bidders</text>
  </g>
  <text x='390' y='1230' class='step-num'>27</text>
  <g transform='translate(420,1210)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Committee picks winner</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Award button in Evaluation tab</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Audit-logged with reason</text>
  </g>
  <text x='720' y='1230' class='step-num'>28</text>
  <g transform='translate(750,1210)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>3 PDFs auto-generated</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Purchase Order · SLA · Contract</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Numbered PMC-PO-YYYY-#####</text>
  </g>
  <text x='1050' y='1230' class='step-num'>29</text>
  <g transform='translate(1080,1210)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Winner notified</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Email + vendor dashboard alert</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Losing bidders auto-refunded EMD</text>
  </g>
  <path class='arrow' d='M350 1125 L420 1125' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 1125 L750 1125' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M1010 1125 L1080 1125' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M350 1255 L420 1255' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 1255 L750 1255' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M1010 1255 L1080 1255' marker-end='url(#ug-arrow)'/>

  <!-- ============ PHASE 5: SIGN + SETTLE ============ -->
  <text x='55' y='1410' class='step-num'>30</text>
  <g transform='translate(90,1390)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Send envelope for signing</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Admin → DocuSign tab</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Embedded OR email delivery</text>
  </g>
  <text x='390' y='1410' class='step-num'>31</text>
  <g transform='translate(420,1390)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Vendor signs</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Vendor dashboard OR email link</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>DocuSign JWT · legally binding</text>
  </g>
  <text x='720' y='1410' class='step-num'>32</text>
  <g transform='translate(750,1390)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Webhook fires</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>envelope-completed event</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>HMAC-verified, status = completed</text>
  </g>
  <text x='1050' y='1410' class='step-num'>33</text>
  <g transform='translate(1080,1390)'>
    <rect class='box-v' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Download signed PDF</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Vendor dashboard · admin log</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>⬇ signed button per envelope</text>
  </g>

  <text x='55' y='1540' class='step-num'>34</text>
  <g transform='translate(90,1520)'>
    <rect class='box-s' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Escrow dual sign-off</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>PMC officer + Escrow officer</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Release button unlocks</text>
  </g>
  <text x='390' y='1540' class='step-num'>35</text>
  <g transform='translate(420,1520)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Funds move</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Release / Refund / Forfeit</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Ledger row · immutable trail</text>
  </g>
  <text x='720' y='1540' class='step-num'>36</text>
  <g transform='translate(750,1520)'>
    <rect class='box-a' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Milestone deliverables</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Contract milestones tracked</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Auto-invoice via Engagements</text>
  </g>
  <text x='1050' y='1540' class='step-num'>37</text>
  <g transform='translate(1080,1520)'>
    <rect class='box-hi' width='260' height='90' rx='8'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Project closed</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Snapshots to /docs/reports</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>Audit log preserved</text>
  </g>
  <path class='arrow-a' d='M350 1435 L420 1435' marker-end='url(#ug-arrow-admin)'/>
  <path class='arrow-v' d='M680 1435 L750 1435' marker-end='url(#ug-arrow-vendor)'/>
  <path class='arrow' d='M1010 1435 L1080 1435' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M350 1565 L420 1565' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M680 1565 L750 1565' marker-end='url(#ug-arrow)'/>
  <path class='arrow' d='M1010 1565 L1080 1565' marker-end='url(#ug-arrow)'/>

  <!-- Footer note -->
  <text x='40' y='1690' class='sub' font-size='11' fill='#64748b'>
    Roles at a glance · Admin = PMC operations · Vendor = supplier bidding · Staff = Escrow · Certifier · Legal · Accounting · Committee · System events fire from webhooks or backend jobs
  </text>
</svg>"""
