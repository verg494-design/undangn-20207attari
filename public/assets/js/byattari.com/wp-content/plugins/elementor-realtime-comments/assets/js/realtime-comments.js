/**
 * Realtime Comments JavaScript
 * Version: 2.1
 */

let loadComments;
let lastId = 0;

document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('realtime-comments');
    if (!container) return;

    const postId = container.getAttribute('data-post-id');

    /**
     * Load comments with pagination
     */
    loadComments = async function (page = 1) {
        try {
            const perPage = container.getAttribute('data-per-page') || 10;

            const list = container.querySelector('ul');
            if (list) list.classList.add('fade-out');

            const response = await fetch(
                realtimeCommentsData.ajaxUrl + 
                '?action=get_realtime_comments&post_id=' + postId + 
                '&page=' + page +
                '&per_page=' + perPage
            );
            const result = await response.json();

            if (result.success && result.data.updated) {
                setTimeout(() => {
                    container.innerHTML = result.data.html;
                    container.scrollTop = 0;

                    const newList = container.querySelector('ul');
                    if (newList) newList.classList.remove('fade-out');
                }, 300);
            }
        } catch (error) {
            console.error('Error loading comments:', error);
            const list = container.querySelector('ul');
            if (list) list.classList.remove('fade-out');
        }
    };

    // Initial load
    loadComments();

    /**
     * Handle delete comment button
     */
    container.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-comment-btn')) {
            const commentId = e.target.getAttribute('data-comment-id');
            if (confirm('Yakin mau hapus komentar ini?')) {
                fetch(realtimeCommentsData.ajaxUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: new URLSearchParams({
                        action: 'delete_comment',
                        comment_id: commentId,
                        _ajax_nonce: realtimeCommentsData.deleteNonce
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadComments();
                    } else {
                        alert('Gagal hapus komentar: ' + (data.data || 'Unknown error'));
                    }
                })
                .catch(error => console.error('Error deleting comment:', error));
            }
        }
    });

    /**
     * Handle pagination buttons
     */
    container.addEventListener('click', function(e) {
        if (e.target.classList.contains('page-btn')) {
            const newPage = parseInt(e.target.getAttribute('data-page'));
            loadComments(newPage);
        }
    });
});

/**
 * Handle Elementor Form Submission - Auto Refresh Comments
 */
jQuery(document).ready(function($) {
    const targetFormId = 'formRSVP';

    function refreshComments(source = '') {
        console.log(`🔄 Refresh komentar via: ${source}`);
        if (typeof loadComments === 'function') {
            lastId = 0;
            loadComments();
        } else {
            console.warn('⚠️ loadComments tidak ditemukan');
        }
    }

    // Listen to Elementor Pro form success event
    $(document).on('elementor-pro/forms/submit/success', function(event, response, form) {
        if (form.attr('id') === targetFormId) {
            refreshComments('event sukses');
        }
    });

    // Listen to Elementor Pro form error event
    $(document).on('elementor-pro/forms/submit/error', function(event, response, form) {
        if (form.attr('id') === targetFormId) {
            refreshComments('event gagal');
        }
    });

    // Mutation Observer - fallback untuk mendeteksi pesan sukses/error
    const targetForm = document.getElementById(targetFormId);
    if (targetForm) {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        if (node.classList.contains('elementor-message') || 
                            node.classList.contains('elementor-message-success') || 
                            node.classList.contains('elementor-message-danger')) {
                            refreshComments('mutation observer');
                        }
                    }
                });
            });
        });

        observer.observe(targetForm, {
            childList: true,
            subtree: true
        });
    }
});