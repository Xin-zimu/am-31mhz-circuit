from run_s05 import prepare,transient

if __name__=='__main__':
    prepare()
    for tag,rd,cd,rf,cf in [('f1',4700,100,4700,100),('f2',2200,100,4700,100),('f3',4700,47,4700,100)]:
        for wave in ['sine','square']:
            transient(tag+'_'+wave,dc_return='direct',rd=rd,cd=cd,rf=rf,cf=cf,wave=wave,duty=.1)
