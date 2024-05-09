import asyncio

from tools_adGroup import AdGroupTools
from tools_db_sp import DbSpTools
from tools_db_new_sp import DbNewSpTools
from datetime import datetime
from ai.backend.util.db.db_amazon.generate_tools import ask_question


db_info = {'host': '****', 'user': '****', 'passwd': '****', 'port': 3306,
               'db': '****',
               'charset': 'utf8mb4', 'use_unicode': True, }

# 创建广告组
def create_adgroup(market,campaignId,name,state,defaultBid):
    adgroup_info = {
        "adGroups": [
            {
                "campaignId": campaignId,
                "name": name,
                "state": state,
                "defaultBid": defaultBid
            }
        ]
    }
    apitool = AdGroupTools()
    res = apitool.create_adGroup_api(adgroup_info)
    # 根据结果更新log
    #     def create_sp_adgroups(self,market,campaignId,adGroupName,adGroupId,state,defaultBid,adGroupState,update_time):
    dbNewTools = DbNewSpTools()
    if res[0]=="success":
        dbNewTools.create_sp_adgroups(market,campaignId,name,res[1],state,defaultBid,"success",datetime.now())
    else:
        dbNewTools.create_sp_adgroups(market,campaignId,name,res[1],state,defaultBid,"failed",datetime.now())

# 新建测试
# res = create_adgroup('US','513987903939456','20240507test','PAUSED',2)
# print(res)

# 更新广告组v0 简单参数
def update_adgroup_v0(market,adGroupName,adGroupId,state,defaultBid_new):
    adgroupInfo = {
        "adGroups": [
            {
                "name": adGroupName,
                "state": state,
                "adGroupId": adGroupId,
                "defaultBid": defaultBid_new
            }
        ]
    }
    # 执行更新
    apitool = AdGroupTools()
    apires = apitool.update_adGroup_api(adgroupInfo)
    # 记录
    #      def update_sp_adgroups(self,market,adGroupName,adGroupId,bid_old,bid_new,standards_acos,acos,beizhu,status,update_time):
    newdbtool = DbNewSpTools()
    if apires[0] == "success":
        print("api update success")
        newdbtool.update_sp_adgroups(market, adGroupName, adGroupId, None,defaultBid_new,None, None, None, "success", datetime.now())
    else:
        print("api update failed")
        newdbtool.update_sp_adgroups(market, adGroupName, adGroupId, None, defaultBid_new, None, None, None, "failed",
                                     datetime.now())

# 测试
# update_adgroup_v0('US','adgroupB09ZQLY99J','311043566627712','PAUSED',4.00)


# 更新广告组
def update_batch_adgroup(market,startdate,enddate,start_acos,end_acos,adjuest):
    '''1.先查找需要更新的adgroup
            2.将需要更新的数据插入到log表记录
            3.开始逐条api更新
            4.更新log表states记录更新状态'''

    apitool = AdGroupTools()
    newdbtool = DbNewSpTools()

    # 1.查找广告组
    dst = DbSpTools(db_info)
    res = dst.get_sp_adgroup_update(market, startdate, enddate, start_acos, end_acos, adjuest)
    print(type(res))
    for i in range(len(res)):
        row = res.iloc[i]
        print(row)
        # 接下来更新操作
        # 新增：adgroup的bid去api获取再去更新 20240506
        adGroupId = row['adGroupId']
        defaultBid_old = apitool.get_adGroup_api(market,adGroupId)
        defaultBid_new = defaultBid_old*(1+adjuest)
        #
        adgroupInfo = {
            "adGroups": [
                {
                    "name": row['adGroupName'],
                    "state": "ENABLED",
                    "adGroupId": row['adGroupId'],
                    "defaultBid": defaultBid_new
                }
            ]
        }
        apires = apitool.update_adGroup_api(adgroupInfo)
        if apires[0]=="success":
            print("api update success")
            newdbtool.update_sp_adgroups(row['market'],row['adGroupName'],row['adGroupId'],defaultBid_old,defaultBid_new,
                                         row['standards_acos'],row['acos'],adjuest,"success",datetime.now())
        else:
            print("api update failed")
            newdbtool.update_sp_adgroups(row['market'], row['adGroupName'], row['adGroupId'], defaultBid_old,
                                         defaultBid_new,
                                         row['standards_acos'], row['acos'], adjuest, "failed", datetime.now())


def add_adGroup_negative_keyword(market,campaignId,adGroupId,matchType,state,keywordText):

    # 翻译注意
    translate_kw = asyncio.get_event_loop().run_until_complete(ask_question(keywordText, market))
    keywordText_new = eval(translate_kw)[0]
    # keywordText_new = keywordText
    #
    adGroup_negative_keyword_info = {
  "negativeKeywords": [
    {
      "campaignId": campaignId,
      "matchType": matchType,
      "state": state,
      "adGroupId": adGroupId,
      "keywordText": keywordText_new
    }
  ]
}
    # api更新
    apitool = AdGroupTools()
    apires = apitool.add_adGroup_negativekw(adGroup_negative_keyword_info)
    # 结果写入日志
    #  def add_sp_adGroup_negativeKeyword(self, market, adGroupName, adGroupId, campaignId, campaignName, matchType,
    #                                         keyword_state, keywordText, campaignNegativeKeywordId, operation_state,
    #                                         update_time):
    newdbtool = DbNewSpTools()
    if apires[0] == "success":
        newdbtool.add_sp_adGroup_negativeKeyword(market, None, adGroupId, campaignId, None, matchType, state, keywordText,keywordText_new,
                                                  apires[1], "success", datetime.now())
    else:
        newdbtool.add_sp_adGroup_negativeKeyword(market, None, adGroupId, campaignId, None, matchType, state, keywordText,keywordText_new,
                                                  apires[1], "success", datetime.now())


# 给广告组更新否定关键词
def update_adGroup_negative_keyword(market,adGroupNegativeKeywordId,keyword_state):
    adGroup_negativekw_info = {
    "negativeKeywords": [
    {
    "keywordId": adGroupNegativeKeywordId,
    "state": keyword_state
    }
    ]
    }
    # api更新
    apitool = AdGroupTools()
    apires = apitool.update_adGroup_negativekw(adGroup_negativekw_info)
    # 结果写入日志
    # def update_sp_adGroup_negativeKeyword(self, market, keyword_state, keywordText, campaignNegativeKeywordId,
    #                                            operation_state, update_time):
    newdbtool = DbNewSpTools()
    if apires[0]=="success":
        newdbtool.update_sp_adGroup_negativeKeyword(market,keyword_state,None,adGroupNegativeKeywordId,"success",datetime.now())
    else:
        newdbtool.update_sp_adGroup_negativeKeyword(market,keyword_state,None,adGroupNegativeKeywordId,"failed",datetime.now())
# 广告组更新否定关键词测试
# update_adGroup_negative_keyword('US','426879824500654','PAUSED')

# 广告组新增否定关键词测试
# add_adGroup_negative_keyword('US','531571979684792','311043566627712','NEGATIVE_EXACT',"ENABLED","冷天装备")

# 更新测试以下为出价规则
# update_adgroup('US','2024-03-01','2024-03-31',-0.99,-0.3,0.1) # ACOS值低于基础值30%的：基础出价提升10%
# update_adgroup('US','2024-03-01','2024-03-31',-0.3,-0.2,0.05) # ACOS值低于基础值20%-30%的：基础出价提升5%
# update_adgroup('US','2024-03-01','2024-03-31',-0.2,-0.1,0.03) # ACOS值低于基础值10%-20%的：基础出价提升3%
# update_adgroup('US','2024-03-01','2024-03-31',0.3,100,-0.15) # ACOS值高于基础值30%的：基础出价降低15%
# update_adgroup('US','2024-03-01','2024-03-31',0.2,0.3,-0.1) # ACOS值高于基础值20%-30%的：基础出价降低10%
# update_adgroup('US','2024-03-01','2024-03-31',0.1,0.2,-0.05) # ACOS值高于基础值10%-20%的：基础出价降低5%
