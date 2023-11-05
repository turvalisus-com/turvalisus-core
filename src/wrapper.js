// noinspection JSUnusedGlobalSymbols
/// <reference path="https://cdn.jsdelivr.net/npm/axios@0.24.0/dist/axios.min.js" />

class TurvalisusAPI {

    // /user/*

    static async createUser(nickname) {
        return await this._post(['user', 'create'], {nickname: nickname});
    }

    static async getUserNickname() {
        return await this._get(['user', 'nickname'])
    }

    static async getUserPoints() {
        return await this._get(['user', 'points'])
    }

    static async logOut() {
        return await this._post(['user', 'logout'])
    }

    // /settings/*

    static async setUserLanguage(lang) {
        return await this._post(['settings', 'language'], {lang: lang})
    }

    // /task/*

    static async getAvailableTasks() {
        return await this._get(['task', 'all'])
    }

    static async submitTaskAnswer(page, option) {
        return await this._post(['task', 'submit'], {page: page, option: option})
    }

    static async submitQuizAnswer(page, answers) {
        return await this._post(['task', 'submit'], {page: page, option: answers, quiz: true})
    }

    // /api/*

    static async getStatistics(score) {
        return await this._get(['api', 'statistics'], {compare: score})
    }

    static async getAvailableLanguages() {
        return await this._get(['api', 'languages'])
    }

    // Utility methods

    static async _get(path, args) {
        return (await axios({
            method: 'get',
            url: '/' + path.join('/'),
            params: args,
            withCredentials: true
        })).data;
    }

    static async _post(path, args) {
        return (await axios({
            method: 'post',
            url: '/' + path.join('/'),
            params: args,
            withCredentials: true
        })).data
    }

}