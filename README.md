# An Institutional Voting System

SAPP Votes is a Voting Web Application built using Python Django on-top of the SPRO & SAPP platform.

## How it works
Like any other SAPP Platform app, SAPP Votes is a data driven system. This data can be manipulated from the SAPP Admin panel or accessed using a web or mobile client app via the SAPP REST API

1. Settings - A configuration model for the system.
2. Election - Data model for an election
3. Party - A competing party in an election
4. Candidate - A representative of a party in for an election
5. Centre - A voting center or place
6. Voter - An entity registered to cast a vote
7. Vote - A vote placed onm a candidate in an election
8. SyncVotesAction - A model that triggers the syncing of election results
9. CloneElectionAction - An action for copy data from previous elections


## Features
1. Secure
2. Scalable
3. Extendable
4. Utitlity actions, functions for moving voters e.t.c
5. Realtime results using SAPP Realtime


## Technologies
1. Python
2. Django
3. DRF
4. SPRO & SAPP
5. JWT

