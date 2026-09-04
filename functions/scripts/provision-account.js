'use strict';
const admin=require('firebase-admin');
const crypto=require('crypto');
admin.initializeApp();
const db=admin.firestore();
const APP='iis-levi-electoral-v3';
const arg=n=>{const i=process.argv.indexOf('--'+n);return i>=0?process.argv[i+1]:''};
const year=arg('year')||'2026/2027',role=String(arg('role')||'COMMISSIONE').toUpperCase(),username=String(arg('username')||'').trim().toLowerCase(),name=String(arg('name')||'').trim(),scopeClass=String(arg('scope')||'TUTTE').toUpperCase(),password=process.env.PROVISION_PASSWORD||'';
if(!/^20\d{2}\/20\d{2}$/.test(year)||!['COMMISSIONE','DIRIGENTE','VICEPRESIDE','DSGA','SEGRETERIA'].includes(role)||!name||!/^[a-z0-9._-]{3,64}$/.test(username)||password.length<12){console.error('Parametri non validi. Impostare PROVISION_PASSWORD (>=12 caratteri) e specificare --username/--name.');process.exit(2)}
const ref=db.collection('artifacts').doc(APP).collection('public').doc('data').collection('gestione_accessi_'+year.replace('/','_'));
(async()=>{const ex=await ref.where('username','==',username).limit(1).get();if(!ex.empty)throw new Error('Username già esistente.');const salt=crypto.randomBytes(24).toString('hex'),passwordHash=crypto.scryptSync(password,salt,64).toString('hex');const d=await ref.add({name,username,passwordHash,passwordSalt:salt,role,scopeClass,active:true,createdAt:admin.firestore.FieldValue.serverTimestamp(),createdBy:'OFFLINE_PROVISIONING'});console.log('Account creato:',d.id,role,username);process.exit(0)})().catch(e=>{console.error(e.message);process.exit(1)});
