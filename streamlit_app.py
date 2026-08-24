import streamlit as st
from google import genai
from pydantic import BaseModel


class Recipe(BaseModel):
    recipe_name: str
    feature: str
    ingredients: list[str]
    seasonings: list[str]
    steps: list[str]
    cooking_time: str


class RecipeSet(BaseModel):
    recipes: list[Recipe]


st.set_page_config(page_title="AIレシピ比較メーカー", page_icon="🍳")

st.title("🍳 AIレシピ比較メーカー")
st.write("料理名と希望条件を入力すると、Geminiが特徴の異なる5つのレシピを作り、違いを比較します。")


dish_name = st.text_input(
    "料理名を入力してください",
    placeholder="例：肉じゃが、親子丼、ミネストローネ",
)

st.subheader("今回の条件")
st.caption("必要な項目だけ入力してください。空欄は「指定なし」として扱います。")

avoid_ingredients = st.text_input(
    "1. 使いたくない材料",
    placeholder="例：玉ねぎ、砂糖、マヨネーズ",
)

must_ingredients = st.text_input(
    "2. 必ず使いたい材料",
    placeholder="例：牛肉、じゃがいも、昆布だし",
)

taste_preference = st.text_input(
    "3. 味の好み",
    placeholder="例：甘さ控えめ、さっぱり、濃いめ",
)

cooking_time = st.text_input(
    "4. 調理時間",
    placeholder="例：30分以内",
)

cooking_method = st.text_input(
    "5. 調理法",
    placeholder="例：鍋で煮る、フライパンだけ、電子レンジ不可",
)


if st.button("5つのレシピを比較する", type="primary"):
    if not dish_name.strip():
        st.warning("料理名を入力してください。")
        st.stop()

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)

        recipe_prompt = f"""
あなたは家庭料理に詳しい料理研究家です。
「{dish_name}」について、特徴がはっきり異なるレシピを必ず5種類作ってください。

今回の追加条件は以下です。
・使いたくない材料：{avoid_ingredients if avoid_ingredients else "指定なし"}
・必ず使いたい材料：{must_ingredients if must_ingredients else "指定なし"}
・味の好み：{taste_preference if taste_preference else "指定なし"}
・調理時間：{cooking_time if cooking_time else "指定なし"}
・調理法：{cooking_method if cooking_method else "指定なし"}

条件の扱いについて、以下を必ず守ってください。
・「使いたくない材料」に指定されたものは、材料・調味料・だし・トッピングを含めて使用しないでください。
・「必ず使いたい材料」に指定されたものは、原則として5種類すべてのレシピで使用してください。
・味の好み、調理時間、調理法の指定がある場合は、5種類すべてでその条件を守ってください。
・条件同士が矛盾する場合は、無理にレシピを作らず、できるだけ条件に近づけてください。

5種類は、できるだけ次のように方向性を変えてください。
1. 定番
2. 甘め
3. さっぱり
4. 時短
5. コク重視

料理や今回の条件によって上の分類が不自然な場合は、その料理に合う別の5分類に置き換えて構いません。
ただし、5種類の違いが明確に分かるようにしてください。

各レシピには必ず以下を含めてください。
・レシピ名
・特徴
・材料
・調味料
・作り方
・調理時間

材料と調味料には、家庭で再現できる具体的な分量を入れてください。
作り方は、初心者でも分かる順番で書いてください。
必ず5レシピだけを返してください。
"""

        with st.spinner("5つのレシピを作成しています..."):
            recipe_response = client.interactions.create(
                model="gemini-3.7-flash",
                input=recipe_prompt,
                response_format=[
                    {
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": RecipeSet.model_json_schema(),
                    }
                ],
            )

            recipe_set = RecipeSet.model_validate_json(recipe_response.output_text)

        if len(recipe_set.recipes) != 5:
            st.error("5つのレシピを生成できませんでした。もう一度お試しください。")
            st.stop()

        st.subheader(f"「{dish_name}」の5つのレシピ")

        for index, recipe in enumerate(recipe_set.recipes, start=1):
            with st.container(border=True):
                st.markdown(f"### レシピ{index}：{recipe.recipe_name}")
                st.markdown(f"**特徴**  \n{recipe.feature}")
                st.markdown(f"**調理時間**  \n{recipe.cooking_time}")

                st.markdown("**材料**")
                for item in recipe.ingredients:
                    st.markdown(f"- {item}")

                st.markdown("**調味料**")
                for item in recipe.seasonings:
                    st.markdown(f"- {item}")

                st.markdown("**作り方**")
                for step_number, step in enumerate(recipe.steps, start=1):
                    st.markdown(f"{step_number}. {step}")

        analysis_prompt = f"""
次の「{dish_name}」の5つのレシピを比較してください。

今回の条件：
・使いたくない材料：{avoid_ingredients if avoid_ingredients else "指定なし"}
・必ず使いたい材料：{must_ingredients if must_ingredients else "指定なし"}
・味の好み：{taste_preference if taste_preference else "指定なし"}
・調理時間：{cooking_time if cooking_time else "指定なし"}
・調理法：{cooking_method if cooking_method else "指定なし"}

以下の観点で、初心者にも分かる日本語で整理してください。
・主な材料の違い
・調味料の違い
・味の方向性
・調理方法の違い
・調理時間
・それぞれどんな人に向いているか

最後に、5種類の特徴を短く一覧でまとめてください。

レシピデータ：
{recipe_response.output_text}
"""

        with st.spinner("5つのレシピの違いを分析しています..."):
            analysis_response = client.interactions.create(
                model="gemini-3.7-flash",
                input=analysis_prompt,
            )

        st.divider()
        st.header("5つのレシピの違い")
        st.markdown(analysis_response.output_text)

    except KeyError:
        st.error(
            "Gemini APIキーが設定されていません。Streamlit Secretsに "
            "GEMINI_API_KEY を登録してください。"
        )
    except Exception as e:
        st.error("エラーが発生しました。APIキーや通信状態を確認して、もう一度お試しください。")
        with st.expander("エラーの詳細"):
            st.code(str(e))
