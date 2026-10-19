# Multiasset closeout: new exploratory results, no confirmed edge

Four asset attempts completed their lifecycle. ESoriginal2s, GC/euro10s sensitivity have all18pairs/146models each:54complete pairs/438scored model representations. ZB10s stopped at firsttrainAug3, commonusable support below100; no partialmodel result. No active job remains in THIS campaign; account-wide custody is not attested. No heldoutOct1+,P&L,confirmededge,100%NT8paritycertificate orcanonicalBrainwrite.

## Results by asset and observation protocol

| Asset / max observed gap | Available evaluation sessions | Common anchors | Full pair means below own base | Density pair means below own base | Arrival below capacity-matched control | Host wall minutes |
| --- | --- | --- | --- | --- | --- | --- |
| ES /2s |8of12|11,422|0of18|9of18|5of18|23.62|
| GC /10s |12of12|75,682|7of18|11of18|0of18|10.49|
| 6E /10s |11of12|7,880|0of18|4of18|2of18|3.27|
| ZB /10s |No complete model evaluation|Not usable|Not measured|Not measured|Not measured|1.50stop|

Headlineweights are equalperavailable-session, not an anchor-pooled average. Dates not substituted. ES unavailableAug14/20/21/26; euroAug14unavailable. EachassetcalibratedJuly31 before sixtrainAug3–10, evalAug11–26. ES original2s has a different observation estimand from GC/6E10s; do not poolasset means, calltheassetcomparisoncontrolledreplication, orrankprofitabilitybyBrier across differentlabelpopulations. These18configurations are correlated, not18independentreplications.

## Gold: distinguish density, confluence and arrival

Seven fullrepresentation means improve gold's owncontinuousbase, fulldeltaBrierrange−0.00103662 to+0.00133771. Strongestfullpair AVZ200densidad×BT2denso improves11of12sessions, but density-only is better still:−0.00131536 versus−0.00103662 full. Fullrepresentation beatsdensity-only in just1of18pairs. Geometry beatsitscapacitycontrol1of18, arrival0of18, incrementalinteraction9of18. A better fullmodelmean is not evidence that everyaddedfamilyfeaturehelps.

Specific jointarrival cuts answer the narrower question: all5supportedgoldcuts retained, including2unfavorablearrivalcontrols.3of5are belowbothbase/control. Strongerexploratorylead: **AVZ25denso×BT2tick200, insidebothzones and both observedleave/return**.4,308anchors across12sessions; pooledΔBrier×1000=−3.3666vsbase,−0.8446vscapacitycontrol; arrival/controlimproves10of12sessions. The old-zonecut overlaps thiscandidate andisnotindependentcorroboration. Abs50return alsohas favorablepooledmeans butonly4of12sessionsimprovecontrol, so doesnotget samepriority. Five supportedjointcuts do NOT mean5confirmedstrategies. Allcells selectedforinterpretationafteroutcomeinspection; nextprobe must be newfrozen developmentwork, notconfirmation/holdoutopening.

ES and euro have no joint arrival cut meeting the frozen minimum of 2,000 anchors across six sessions. More native zone births do not necessarily produce more eligible paired overlaps. Seeall54pairresults, per-session144+216+198rows, andallobserved17arrivalcuts. Missingunobservedcuts are not inventedzeroBrier scores.

## Timing and operational lessons

Runnerseconds:ES1388.46,GC625.27,euro191.20; hosttimesinclude transport. Sharedfootprintcachehits10.27%/35.53%/17.78%, no sameinputuncached market speedup comparator. BT2Auses66.34%/30.18%/52.66%runner respectively. Do notcompare markets as a measured optimization speedup. Cachehigh eviction and perconfigwholesessionprocessing suggest bounded samebucketinterleaving as nextcandidate; keep eachconfigstate/history independent, nativeeventorderexact, andtestsameinputmarketaggregatesinsideKaggle beforecallingit faster. No nativehistoryshortcut.

Strict2sgap eligibility failed GC/euro/ZB withunsupportedcalibrationcells; one bounded diagnostic measuredcoverage withoutfit/natives orre-auditingdatasets. Explicit10s sensitivity didnotchange dates/minima/quote/signedvolume gates. ZBstillfails; donotquietlyrelaxgapagain. DiagnosticV1bootfailedbeforetransportwithunclassifiedexception; sourceassumed /kaggle/temp. V2standardtempfileroot+closedstagetelemetrycompleted22.84s. Originalterminaljournalsretained, noresets/replays. A local6Ereceiptloader accidentally referencedoldpackage; correcteditslookup andverifiedactualbytes/sealwithout rerunning. GitHubdiscovery transientfailure recoveredbydescribethenretry, notduplicateKagglesubmissions.

## Reproduce and resume

Decode lossless public *_RECEIPT_PACKED JSON, verify original_sha256, then independent review_multiasset_crossfamily withthecorrectfrozenplan. Run scripts/analyze_multiasset_crossfamily.py withthree --receipt arguments andtheroster. Publicreceiptsare aggregatesonly, no ticks/labels/modelcoefficients/private logs. Protectedoperationaljournals under /data/operational-state: multiasset-1fc00c5ad2e4; gap10-e18747ab0efc; support-96b90f0c460a(V1ERROR),support-v2-96b90f0c460a(COMPLETE). Transferoriginaljournalswithapprovedcustody; neverrecreatefromJSONsnapshotsorresetbudgets. KernelIDs/versions/sourcecommits/packageSHAstipsin LAUNCH/CLOSEOUT. SignedsourceURLsremainprivate,expire72h; notpublished.

Nextusefulwork: preregisterspecificgoldreturnquestion onanuntouched developmentblock withsession/episode dependence-awareassessment anddensity/capacity/mirror controls; keep allnegative results. Separately benchmark exactnativebucket sharing. Do notautomaticallydeployDebiandaemon,mergePR117,writecanonicalBrain,orapprovewinners. Knowledgeproposal is PROPOSED_REVIEWED_AGGREGATES_NOT_CANONICAL.918ResearchOps+18navigationtestsPASS,catalogPASS_NAVIGATION_ONLY.
