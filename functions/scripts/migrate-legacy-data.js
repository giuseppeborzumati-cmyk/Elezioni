'use strict';
const admin=require('firebase-admin');
admin.initializeApp();
const db=admin.firestore();
const APP='iis-levi-electoral-v3';
const arg=n=>{const i=process.argv.indexOf('--'+n);return i>=0?process.argv[i+1]:''};
const year=arg('year')||'2026/2027',apply=process.argv.includes('--apply'),s=year.replace('/','_');
const ref=db.collection('artifacts').doc(APP).collection('public').doc('data').collection('tokens_'+s);
(async()=>{const snap=await ref.get();let affected=0;for(const d of snap.docs){const data=d.data(),patch={};for(const k of Object.keys(data))if(/^vote_id_/i.test(k))patch[k]=admin.firestore.FieldValue.delete();if(Object.keys(patch).length){affected++;console.log(apply?'REMOVE':'DRY-RUN',d.id,Object.keys(patch).join(','));if(apply)await d.ref.update(patch)}}console.log('Documenti interessati:',affected,'Modalità:',apply?'APPLY':'DRY-RUN');if(!apply)console.log('Eseguire un backup e poi rilanciare con --apply solo dopo autorizzazione verbalizzata.');process.exit(0)})().catch(e=>{console.error(e);process.exit(1)});
