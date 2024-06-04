# ai-dojo-demo

## Setup

```shell
docker compose up -d --build
```

More information in each README.md in the `images/` subdirectory.

## Scenario

### Summary

1. Thanks to the phishing, one of the clients is attacked (cannot be the testing account, but the same "pc" can) and a session is created.
2. Search for the testing user in the vulnerable servers.
3. Bruteforce the testing user.
4. Read bash history of the testing user.
5. Get access to the database and exfiltrate data.

### Initial attack vector

**Intrusion Scenario: Ecliptic Evasion**

In the radiant halls of Celestial Discoveries Research Institute (CDRI), where cosmic secrets are unveiled, an orchestrated digital intrigue takes shape. Like a nebula forming from stardust, an adversary with stealthy finesse crafts an enigmatic email, adorned with a subject that mimics the cosmic wonders CDRI strives to unravel.

Within this celestial correspondence, the art of social engineering blooms. The message, meticulously tailored to the recipient's professional curiosity, promises glimpses of an otherworldly phenomenon captured through an ethereal lens. The email's veneer of authenticity shines as brilliantly as the distant stars.

Engrossed by cosmic allure, an employee named Dr. Aurora Starcrest, a brilliant astrophysicist with an insatiable curiosity, opens the email. A single click beckons a hidden payload, an arcane emissary of code that awakens dormant power within her workstation. Like a dormant comet flaring to life, the malicious code executes, invoking a connection to the orchestrator beyond the digital veil.

Unbeknownst to CDRI's diligent guardians, a virtual backdoor, artfully concealed, springs open, allowing the attacker to traverse the vast expanse of Dr. Starcrest's machine. It is a symphony of intrusion orchestrated across the vast digital cosmos. Undetected, the backdoor's resonance creates an echo of breached defenses, leaving a dormant but potent channel through which the adversary may traverse at will.

With artful grace, the attacker camouflages their tracks amidst the digital constellations, embedding themselves within the machine's very essence. It's a dance between shadows and bytes, a ballet of data masquerading as benign processes, the essence of intrusion embodied.

As the shimmering auroras above the North Pole enchant, so too does the concealed entry point enchant the adversary. A presence within the hallowed confines of CDRI's digital realm is established—a whisper in the vast silence, a sentinel of untold potential.

As the Celestial Discoveries Research Institute continues its noble pursuit of cosmic comprehension, the breach remains concealed, a dormant comet awaiting its moment to blaze across the firmament. The shadows of intrusion linger, a testament to the ever-present dance between progress and peril, where even the stars are not beyond the reach of calculated trespass.

```
**Subject**: Unveiling the Veil: Cosmic Revelations Await

**Recipient**: Dr. Aurora Starcrest
**From**: Dr. Orion Nightsky <orion.nightsky@cdri.space>
**Date**: [Current Date]

Dear Dr. Starcrest,

I hope this message finds you well amidst the boundless mysteries of the cosmos. In our unrelenting pursuit of celestial revelations, a discovery of unprecedented magnitude has come to light. It is a secret whispered across the nebulous corridors of the universe, a secret we believe the world should know.

Enclosed within this ethereal envelope is a cosmic artifact, captured by our observatory's vigilant gaze. An image, a piece of the heavens beyond, harboring whispers of what lies veiled in the interstellar depths. I implore you, a kindred spirit in the quest for cosmic enlightenment, to cast your inquisitive gaze upon this enigma.

To behold this image is to peer into the heart of a celestial enigma, one that holds the potential to redefine our understanding of the universe. I beseech you, with your keen insight and inimitable expertise, to explore this artifact's potential significance and share your thoughts.

It is in the spirit of collaboration that I send forth this digital missive, a call to arms for those who understand the magnitude of our mission. Respond at your earliest convenience, for the cosmic dance waits for no one, and together, we shall traverse the boundary between the known and the unknown.

Eagerly awaiting your response amidst the starlit tapestry,

Dr. Orion Nightsky
Lead Astronomer
Celestial Discoveries Research Institute (CDRI)
[Contact Number]
[cdri.space]
```

## Company information

### Name
Celestial Discoveries Research Institute (CDRI)

### Background
Established in 20XX, Celestial Discoveries Research Institute (CDRI) stands at the forefront of space research, specializing in the exploration and analysis of items found in space. CDRI's mission is to unravel the mysteries of the universe by studying celestial objects such as meteorites, cosmic dust, and rare extraterrestrial materials. Guided by a team of dedicated scientists, astronomers, geologists, and experts from various fields, CDRI is committed to advancing human knowledge and contributing to the global scientific understanding of the cosmos.

### Workers
CDRI boasts a diverse and talented team, including astrophysicists, chemists, geologists, data scientists, technicians, engineers, and administrative staff. This multidisciplinary approach enables CDRI to comprehensively examine and interpret the data collected from space items. Collaboration is key as team members work in synergy to uncover the secrets of the universe.

**List of Employees at CDRI**:

1. **Dr. Aurora Starcrest**: Astrophysicist
2. **Dr. Orion Nightsky**: Astronomer
3. **Dr. Lyra Stellaria**: Geologist
4. **Dr. Nova Lumina**: Data Scientist
5. **Dr. Solara Celestia**: Research Director
6. **Elena Nebulosa**: System Administrator
7. **Alex Comettrail**: Network Engineer
8. **Oliver Galaxium**: Research Assistant
9. **Sophia Starborne**: Administrative Coordinator
10. **Victor Deepspace**: Security Analyst

### Reasons for Network Topology

1. **Subnet 1 (Client Devices)**: In this isolated Wi-Fi network, client devices such as notebooks and phones used by researchers and staff connect. This setup ensures a secure environment for accessing resources and prevents any direct access to the critical infrastructure, safeguarding sensitive data.
2. **Subnet 2 (Dedicated Workstations)**: CDRI's researchers rely on powerful dedicated workstations in this subnet. It facilitates seamless communication between client devices, the server subnet, and the Internet, enabling efficient sharing of research results while maintaining the security of sensitive information.
3. **Subnet 3 (Server Network)**: The heart of CDRI's operations, this subnet houses the company's critical servers. Hosting services like WordPress, PostgreSQL, Haraka mail server, and vsftpd (FTP server), this subnet ensures the integrity and accessibility of essential tools for research, data management, and communication.

### Server Services

#### CelestialPress
CDRI's WordPress-based platform showcases research findings and educational content to the public. Visitors engage with informative articles and visualizations, fostering a deeper understanding of space discoveries.

#### StellarDB (MySQL)
This comprehensive database centralizes research data, promoting efficient storage, retrieval, and analysis. Its relational architecture facilitates connections between different datasets, enhancing researchers' ability to identify patterns and correlations.

#### CosmicMail (Haraka Mail Server)
The Haraka mail server enables secure communication within CDRI and with external partners. It supports collaboration, information sharing, and project coordination among team members.

#### AstroFTP (vsftpd)
The vsftpd FTP server serves as a secure repository for data storage and sharing. It accommodates large datasets, images, and reports related to space research, promoting effective collaboration.

#### AstroChat (Rocket.Chat)
The Rocket.Chat platform provides real-time communication and collaboration for CDRI's internal team. With text chat, file sharing, and video conferencing capabilities, AstroChat enhances team coordination, information sharing, and project collaboration within a secure and controlled environment.

### Clients

#### Workstation
Workstation represents one machine used by an employee.

Each workstation contains a Humanbot instance (that represents the employee).

#### Workstation with a developer account
Same as the [workstation](#workstation). However, a developer account is present. 

The developer account is used to manage the servers and services and must be present in the second network. 
The account has a deliberately weak password. This account facilitates self-hosted service management, updates, and testing.

It also hosts an SSH server.

[//]: # (#### Phone)

[//]: # (A personal device &#40;phone, tablet, laptop, etc.&#41;.)

[//]: # ()
[//]: # (Otherwise, same as the [workstation]&#40;#workstation&#41;.)

[//]: # ()
[//]: # (#### Laptop)

[//]: # (A personal device &#40;phone, tablet, laptop, etc.&#41;.)

[//]: # ()
[//]: # (Otherwise, same as the [workstation]&#40;#workstation&#41;.)
