import asyncio

from tools_campaign import CampaignTools
from tools_db_sp import DbSpTools
from tools_db_new_sp import DbNewSpTools
from datetime import datetime
from ai.backend.util.db.db_amazon.generate_tools import ask_question


db_info = {'host': '****', 'user': '****', 'passwd': '****', 'port': 3306,
               'db': '****',
               'charset': 'utf8mb4', 'use_unicode': True, }

# 新增广告系列
def create_camapign(market,portfolioId,endDate,name,targetingType,state,startDate,budgetType,budget):
    campaigninfo = {
  "campaigns": [
    {
      "portfolioId": portfolioId,
      "endDate": endDate,
      "name": name,
      "targetingType": targetingType,
      "state": state,
      "dynamicBidding": {
        "placementBidding": [
          {
            "percentage": 0,
            "placement": "PLACEMENT_TOP"
          }
        ],
        "strategy": "LEGACY_FOR_SALES"
      },
      "startDate": startDate,
      "budget": {
        "budgetType": budgetType,
        "budget": budget
      },
      "tags": {
        "property1": "string",
        "property2": "string"
      }
    }
  ]
}
    # 执行创建
    apitool = CampaignTools()
    res = apitool.create_campaigns_api(campaigninfo)
    # 根据创建结果更新log
    dbNewTools = DbNewSpTools()
    if res[0] == "success":
        dbNewTools.create_sp_campaigin(market,portfolioId,endDate,name,res[1],targetingType,state,startDate,budgetType,budget,"success",datetime.now())
    else:
        dbNewTools.create_sp_campaigin(market,portfolioId,endDate,name,res[1],targetingType,state,startDate,budgetType,budget,"failed",datetime.now())

    return res[1]
# create_camapign('US','48203655494067','2024-10-01','DeepBI_20240507_test','MANUAL','PAUSED','2024-06-01','DAILY',0.1)


# 更新广告系列 简单数据更新
def update_camapign_v0(market,campaignId,campaignName,state,budgetType,budget_new,budget_old=None):
    campaign_info = {
        "campaigns": [
            {
                "campaignId": campaignId,
                "name": campaignName,
                "state": state,
                "budget": {
                    "budgetType": budgetType,
                    "budget": budget_new
                },
            }
        ]
    }
    #调用api
    apitool = CampaignTools()
    apires = apitool.update_campaigns(campaign_info)

    # 更新log
    #     def update_sp_campaign(self,market,campaign_name,campaign_id,budget_old,budget_new,standards_acos,acos,beizhu,status,update_time):
    newdbtool = DbNewSpTools()
    if apires[0] == "success":
        print("api update success")
        newdbtool.update_sp_campaign(market, campaignName, campaignId,budget_old,budget_new,None,None,"","success",datetime.now())
    else:
        print("api update failed")
        newdbtool.update_sp_campaign(market, campaignName, campaignId, budget_old, budget_new, None, None, "", "failed",
                                     datetime.now())

# update v0 测试
# update_camapign_v0('US','531571979684792','B09ZQLY99J-2024-03-29','PAUSED','DAILY',2)


# 更新 根据要求自动批量更新
def update_camapign(market,startdate,enddate,start_acos,end_acos,adjuest):
    '''先查找需要更新的campaign活动
        开始逐条api更新
        更新log表states记录更新状态'''

    apitool = CampaignTools()
    newdbtool = DbNewSpTools()

    # 1.获取数据
    dst = DbSpTools(db_info)
    res = dst.get_sp_SkuAdgroupCamapign(market,startdate,enddate,start_acos,end_acos,adjuest)
    print(type(res))
    for i in range(len(res)):
        row = res.iloc[i]
        # 现在 row 是一个 Series 对象，你可以通过整数位置索引或者列名来访问每个值
        # 例如，row[0] 表示第一个值，row['column_name'] 表示指定列名的值
        print(row)
        print(row['budget_new'])
        campaign_info = {
            "campaigns": [
                {
                    "campaignId": row['campaignId'],
                    "name": row['campaignName'],
                    "budget": {
                        "budgetType": "DAILY",
                        "budget": row['budget_new']
                    },
                }
            ]
        }
        # newdbtool.update_sp_campaign(row['market'], row['campaignName'], row['campaignId'], row['budget_old'],
        #                              row['budget_new'],
        #                              float(row['standards_acos']), float(row['acos']),row['beizhu'], "failed", datetime.now())

        apires = apitool.update_campaigns(campaign_info)
        if apires[0]=="success":
            print("api update success")
            newdbtool.update_sp_campaign(row['market'],row['campaignName'],row['campaignId'],row['budget_old'],row['budget_new'],
                                         row['standards_acos'],row['acos'],"success",datetime.now())
        else:
            print("api update failed")
            newdbtool.update_sp_campaign(row['market'], row['campaignName'], row['campaignId'], row['budget_old'],
                                         row['budget_new'],
                                         row['standards_acos'], row['acos'], "failed", datetime.now())


# 更新广告系列的placement
# 按照顺序进行传入
def update_campaign_placement(market,campaignId,p_top_percentage,p_res_of_search_percentage,p_product_page_percentage):
    campaign_placement_info = {
        "campaigns": [
            {
                "campaignId": campaignId,
                "dynamicBidding": {
                    "placementBidding": [
                        {
                            "percentage": p_top_percentage,
                            "placement": "PLACEMENT_TOP"
                        },
                        {
                            "percentage": p_res_of_search_percentage,
                            "placement": "PLACEMENT_REST_OF_SEARCH"
                        },
                        {
                            "percentage": p_product_page_percentage,
                            "placement": "PLACEMENT_PRODUCT_PAGE"
                        },
                    ],
                },
            }
        ]
    }

    # api更新
    apitool = CampaignTools()
    res = apitool.update_campaigns(campaign_placement_info)
    # 根据结果写入日志
    #     def update_sp_campaign_placement(self,market,campaignId,p_top,p_top_percentage,p_res_of_search,p_res_of_search_percentage,p_product_page,p_product_page_percentage,status,update_time):
    newdbtool = DbNewSpTools()
    if res[0]=="success":
        newdbtool.update_sp_campaign_placement(market,campaignId,"PLACEMENT_TOP",p_top_percentage,"PLACEMENT_REST_OF_SEARCH",p_res_of_search_percentage,"PLACEMENT_PRODUCT_PAGE",p_product_page_percentage,"success",datetime.now())
    else:
        newdbtool.update_sp_campaign_placement(market, campaignId, "PLACEMENT_TOP", p_top_percentage,
                                               "PLACEMENT_REST_OF_SEARCH", p_res_of_search_percentage,
                                               "PLACEMENT_PRODUCT_PAGE", p_product_page_percentage, "failed",
                                               datetime.now())
# 更新placement测试
# update_campaign_placement('US','531571979684792',0,0,0)

# 给广告系列新增否定关键词
def add_campaigin_negative_keyword(market,campaignId,matchType,state,keywordText):
    # 翻译注意
    translate_kw = asyncio.get_event_loop().run_until_complete(ask_question(keywordText, market))
    keywordText_new = eval(translate_kw)[0]

    campaigin_negative_keyword_info = {
  "campaignNegativeKeywords": [
    {
      "campaignId": campaignId,
      "matchType": matchType,
      "state": state,
      "keywordText": keywordText_new
    }
  ]
}
    # api更新
    apitool = CampaignTools()
    apires = apitool.add_campaigns_negative_keywords(campaigin_negative_keyword_info)
    # 结果写入日志
    #     def add_sp_campaign_negativeKeyword(self,market,adGroupName,adGroupId,campaignId,campaignName,matchType,keyword_state,keywordText,campaignNegativeKeywordId,operation_state,update_time):
    newdbtool = DbNewSpTools()
    if apires[0]=="success":
        newdbtool.add_sp_campaign_negativeKeyword(market,None,None,campaignId,None,matchType,state,keywordText,keywordText_new,apires[1],"success",datetime.now())
    else:
        newdbtool.add_sp_campaign_negativeKeyword(market, None, None, campaignId, None, matchType, state, keywordText,keywordText_new,None,
                                                  "failed", datetime.now())


# 给广告系列更新否定关键词
def update_campaigin_negative_keyword(market,campaignNegativeKeywordId,keyword_state):
    campaigin_negative_keyword_info = {
  "campaignNegativeKeywords": [
    {
      "keywordId": campaignNegativeKeywordId,
      "state": keyword_state
    }
  ]
}
    # api更新
    apitool = CampaignTools()
    apires = apitool.update_campaigns_negative_keywords(campaigin_negative_keyword_info)
    # 结果写入日志
    #     def update_sp_campaign_negativeKeyword(self, market,keyword_state, keywordText, campaignNegativeKeywordId, operation_state,update_time):
    newdbtool = DbNewSpTools()
    if apires[0]=="success":
        newdbtool.update_sp_campaign_negativeKeyword(market,keyword_state,None,campaignNegativeKeywordId,"success",datetime.now())
    else:
        newdbtool.update_sp_campaign_negativeKeyword(market, keyword_state, None, campaignNegativeKeywordId, "failed",datetime.now())


# 修改关键词状态测试：
# update_campaigin_negative_keyword('US','428799562608462','PAUSED')
# 增加否定关键词测试
# add_campaigin_negative_keyword('US',"531571979684792","NEGATIVE_PHRASE","ENABLED","冷天装备")

# 测试
# update_camapign('US','2024-03-01','2024-03-31',0.1,0.2,-0.1) # 高于平均ACOS值10% - 20%的 预算降低10%
# update_camapign('US','2024-03-01','2024-03-31',0.2,0.3,-0.2) # 高于平均ACOS值20% - 30%的 预算降低20%
# update_camapign('US','2024-03-01','2024-03-31',0.3,100,-0.3) # 高于平均ACOS值30% 以上 预算降低30%
# update_camapign('US','2024-03-01','2024-03-31',-0.99,-0.3,0.3) # 低于 平均ACOS值 10% - 20%的：预算提升30%
# update_camapign('US','2024-03-01','2024-03-31',-0.3,-0.2,0.2) # 低于 平均ACOS值 20% - 30%的：预算提升20%
# update_camapign('US','2024-03-01','2024-03-31',-0.2,-0.1,0.1) # 低于 平均ACOS值 30% 以上的 预算提升10%
