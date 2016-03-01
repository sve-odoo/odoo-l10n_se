# -*- coding: utf-8 -*-
from cStringIO import StringIO
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import http
import base64
import tempfile
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response
import re

import logging
_logger = logging.getLogger(__name__)

class account_sie(models.TransientModel):
    _name = 'account.sie'
    _description = 'Odoo'
       
    date_start = fields.Date(string = "Start Date")
    date_stop = fields.Date(string = "Stop Date")
    start_period = fields.Many2one(comodel_name = "account.period", string = "Start Period")
    stop_period = fields.Many2one(comodel_name = "account.period", string = "Stop Period")
    fiscal_year = fields.Many2one(comodel_name = "account.fiscalyear", string = "Fiscal Year")
    journal = fields.Many2many(comodel_name = "account.journal", string = "Journal")
    account = fields.Many2many(comodel_name = "account.account", relation='table_name', string = "Account")
    
    state =  fields.Selection([('choose', 'choose'), ('get', 'get')],default="choose") 
    data = fields.Binary('File')
    
    def _stringSplit(self, string):
        tempString = ""
        splitList = []
        quote = False
        for s in range(0, len(string)):
            if (not quote and string[s] == '"'):
                quote = True
                tempString += string[s]
            elif (quote and string[s] == '"'):
                quote = False
                tempString += string[s]
                if (len(tempString) > 0):
                    splitList.append(tempString)
                tempString = ""
            elif (quote and string[s] == ' '):
                tempString += string[s]
            elif (not quote and string[s] == ' '):
                if (len(tempString) > 0):
                    splitList.append(tempString)
                tempString = ""
            elif (not quote and s == len(string)-1 and not string[s] == ' '):
                tempString += string[s]
                splitList.append(tempString)
            else:
                tempString += string[s]
        return splitList
    
    def _import_accounts(self, string):
        list_of_accounts = []
        accounts = []
        for account in re.finditer(re.compile(r'(#KONTO .+)+', re.MULTILINE), string):
            list_of_accounts.append(account.group())
        for x in (list_of_accounts):
            tmpvar = self._stringSplit(x)
            accounts.append((tmpvar[1],tmpvar[2]))
        return accounts
    
    def _import_ver(self,string):
        for ver in re.finditer(re.compile(r'#VER .+\n{\n(#TRANS .+\n)+}\n', re.MULTILINE), string):
            verString = '' + (re.search(re.compile(r'#VER .+'),ver.group()).group())
            verList = self._stringSplit(verString)
            list_date = verList[3]  # date
            list_ref = verList[2]   # reference
            list_sign = verList[5]  # sign
            

                
            
            #~ #self.env['account.period'].find(dt=FIXA DATUMET FRÅN FIL STRÄNG)
            #~ #self._uid self._cr eventuellt skicka med
            
            ver_date = (self.env['account.period'].find(dt=list_date))
            # ver_date ger ett id.
            
            #atm always GENERAL journal
            journal = self.env['account.journal'].search([('type','=','general')])
            if journal:
                journal = journal[0].id
            

#VER "" BNK2/2016/0001 20160216 "" admin
            if len(ver_date)>0:
                ver_id = self.env['account.move'].create({
                    'period_id': self.env['account.period'].find(dt=list_date).id,
            #~ '''            #~ 'period_id': , # SÖK rätt period utifrån datum '''
                    'journal_id': journal,
                    })
                _logger.warning('VER %s' %ver_id)
                

#~ #VER "" SAJ/2016/0002 20150205 "" admin
#~ {
#~ #TRANS kontonr   {objektlista}   belopp transdat transtext   kvantitet   sign
#~ #TRANS 1510      {}              -100.0 20150205 "/"         1.0         admin
#~ #TRANS 2610 {} 0.0 20150205 "Försäljning 25%" 1.0 admin
#~ #TRANS 3000 {} 0.0 20150205 "Skor" 1.0 admin
#~ }
            
            
            for trans in re.findall(re.compile('#TRANS .+'),ver.group()):
                transList = self._stringSplit(trans)
                args = len(transList)
                # these should always be set args <= 4
                trans_code = transList[1]
                trans_object = transList[2]
                trans_balance = transList[3]
                if args >=5:
                    trans_date = transList[4]
                if args >= 6:
                    trans_name = transList[5]
                if args >= 7:
                    trans_quantity = transList[6]
                
                trans_sign = transList[len(transList)-1]
                user = self.env['res.users'].search([('login','=',trans_sign)])
                if user:
                    user = user[0].id
                
                code = self.env['account.account'].search([('code','=',trans_code)])
                #~ raise Warning('%s\n%s' %(code, code[0].code))
                if code:
                    code = code[0].code
                
                #~ raise Warning(self.env['account.move.line'].search([])[0].date)
                _logger.warning('\naccount_id :%s\nbalance: %s\njournal_id: %s\nperiod_id: %s' %(code,trans_balance,journal,self.env['account.period'].find(dt=list_date).id))

                period_id = self.env['account.period'].find(dt=list_date).id                
                
                trans_id = self.env['account.move.line'].create({
                    'account_id': code,
                    'credit': float(trans_balance) < 0 and float(trans_balance) or 0.0,
                    'debit': float(trans_balance) > 0 and float(trans_balance) or 0.0,
                  #  'journal_id': journal,
                    'period_id': period_id,
                    'date': '' + trans_date[0:4] + '-' + trans_date[4:6] + '-' + trans_date[6:],
                    #'quantity': trans_quantity,
                    #'name': trans_name,
                    #'create_uid': user,
                    })
    
        
        
    @api.multi
    def send_form(self):
        sie_form = self[0]
        if not sie_form.data == None: # IMPORT TRIGGERED
            #~ fileobj = TemporaryFile('w+')
            #~ fileobj.write(base64.decodestring(sie_form.data))
            #~ fileobj.seek(0)
            #~ try:
                #~ pass
            #    #~ tools.convert_xml_import(account._cr, 'account_export', fileobj, None, 'init', False, None)
            #~ finally:
                #~ fileobj.close()
            #return True
            #~ # select * from account_period where accunt_period.period_id >= p1 and accunt_period.period_id <= p2
            tempString = '' + base64.decodestring(sie_form.data)
            
            missing_accounts = self.env['account.account'].check__missing_accounts(self._import_accounts(tempString))
                        
            if len(missing_accounts) > 0:
                raise Warning(_('Accounts missing, add before import\n%s') % '\n '.join(['%s %s' %(a[0],_(a[1])) for a in missing_accounts]))
            
            self._import_ver(tempString)


                #~ 
            #self.env['l10n_se_sie_importfile'].get_ver_trans(tempString)
            # vill hja en lista med konton och verifikat
            # 
            
            
        ## TODO: plenty of if cases to know what's selected. id is integer
        if(sie_form.start_period.id and sie_form.stop_period.id):
            period_ids = [p.id for p in sie_form.env['account.period'].search(['&',('id','>=',sie_form.start_period.id),('id','>=',sie_form.stop_period.id)])]
            s = [('period_id','in',period_ids)]
        else:
            s = [('period_id','in',[])]
        #raise Warning(s)
        sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie(search=s)) })
        #~ sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie()) })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.sie',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': sie_form.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
    
    
    @api.multi
    def make_sie(self,search=[]):
        #raise Warning("make_sie: %s %s" %(self,search))
        #  make_sie: account.sie() [('period_id', 'in', [3])] 
        if len(self) > 0:
            sie_form = self[0]
        account_list = set()
        for line in self.env['account.move.line'].search(search):
            account_list.add(line.account_id.code)
        str = ''
        for code in account_list:
            str += '#KONTO %s\n' % code  
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))  
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
    
        for ver in self.env['account.move'].search(search):
            str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, self.fix_narration(ver.narration), ver.create_date, ver.create_uid.login)
            #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %f %s "%s" %s %s \n' % (trans.account_id.code, trans.balance, trans.date, self.fix_narration(trans.name), trans.quantity, trans.create_uid.login)
            str += '}\n'
        return str
    
    @api.multi
    def get_accounts(self,ver_ids):
        account_list = set()
        for ver in ver_ids:
            for line in ver.line_id:
            #for l in ver.line_id for ver in ver_ids]]:
                account_list.add(line.account_id)
        return account_list
        
    
    @api.multi
    def get_fiscalyears(self,ver_ids):
        year_list = set()
        for ver in ver_ids:
            year_list.add(ver.period_id.fiscalyear_id)
        return year_list
        
    
    @api.multi
    def make_sie2(self, ver_ids):
        if len(self) > 0:
            sie_form = self[0]
        
        company = ver_ids[0].company_id
        fiscalyear = ver_ids[0].period_id.fiscalyear_id
        user = self.env['res.users'].browse(self._context['uid'])

        str = ''
        str += '#FLAGGA 0\n' 
        str += '#PROGRAM "Odoo" 8.0.1\n'
        str += '#FORMAT PC8, Anger vilken teckenuppsattning som anvants\n'
        str += '#GEN %s\n'%fields.Date.today().replace('-','')
        str += '#SIETYP 4i\n'
        for fiscalyear in self.get_fiscalyears(ver_ids):
            str += '#RAR %s %s %s\n' %(fiscalyear.get_rar_code(), fiscalyear.date_start.replace('-',''), fiscalyear.date_stop.replace('-',''))
        str += '#ORGNR %s\n' %company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' %(user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' % company.kptyp
        for account in self.get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
            
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))  
        
        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
    
        for ver in ver_ids:
            str += '#VER "" %s %s "%s" %s\n{\n' % (ver.name, ver.date.replace('-',''), self.fix_empty(ver.narration), ver.create_uid.login)
            #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
            
            for trans in ver.line_id:
                str += '#TRANS %s {} %s %s "%s" %s %s\n' % (trans.account_id.code, trans.balance, trans.date.replace('-',''), self.fix_empty(trans.name), trans.quantity, trans.create_uid.login)
            str += '}\n'
        
        _logger.warning('\n%s\n' % str)
        
        return str
    
    @api.multi
    def export_sie(self,ver_ids):
        if len(self) < 1:
            sie_form = self.create({})
        else:
            sie_form=self[0]
        sie_form.write({'state': 'get', 'data': base64.b64encode(sie_form.make_sie2(ver_ids).encode('utf8')) })
        #~ sie_form.write({'state': 'get', 'data': base64.b64encode(self.make_sie()) })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.sie',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': sie_form.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
    # if narration is null, return empty string instead of parsing to False
    @api.multi
    def fix_empty(self, narration):
        if(narration):
            return narration
        else:
            return ''
        
        ''' 
    def sietyp(self):
        return correct type. some if cases.
        Typ 1 Årssaldon. Innehåller årets ingående och utgående saldon för samtliga konton i kontoplanen
        Typ 2 Periodsaldon. Innehåller all information från typ 1 samt månadsvisa saldoförändringar för samtliga konton.
        Typ 3 Objektsaldon. Identisk med typ 2, men saldon finns även på objektnivå, t ex kostnadsställen och projekt.
        Typ 4 Transaktioner. Identisk med typ 3, men innehåller även samtliga verifikationer för räkenskapsåret. Detta filformat kan användas för export av årets grundboksnoteringar till ett program för transaktionsanalys
        Typ 4i Transaktioner. Innehåller endast verifikationer. Filformatet används när ett försystem, t ex ett löneprogram eller ett faktureringsprogram ska generera bokföringsorder för inläsning i bokföringssystemet.
        '''
    @api.multi
    def import_sie(self):
        sie_form = self[0]
        raise Warning(sie_form.data)
        #~ result = {}
        #~ for product_data in self.browse(cr, uid, ids, context=context):
                #~ result[product_data.id] = product_data['file_path']
                #~ return result
        #~ return result

        #_logger.warning('\n%s' % base64.encodestring(args.get('data').read()))
        
