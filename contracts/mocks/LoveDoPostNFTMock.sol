// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title LoveDoPostNFTMock
 * @dev Mock for LoveEmissionEngine tests. Implements the interface expected by the engine:
 *   getPost(tokenId), addSuperlike(tokenId) returns (bool), getLoveDoCount(seller).
 *   addPostForTest(author, sellerTo, linkedSeller) to create a post and get tokenId.
 */
contract LoveDoPostNFTMock {
    struct Post {
        address author;
        address sellerTo;
        address linkedSeller;
        uint8 superlikes;
    }

    mapping(uint256 => Post) private _posts;
    uint256 private _nextTokenId;
    mapping(address => uint256[]) private _postsBySeller;
    mapping(uint256 => mapping(address => bool)) public hasSuperliked;

    function nextTokenId() external view returns (uint256) {
        return _nextTokenId;
    }

    function addPostForTest(address author, address sellerTo, address linkedSeller) external returns (uint256 tokenId) {
        tokenId = _nextTokenId++;
        _posts[tokenId] = Post({ author: author, sellerTo: sellerTo, linkedSeller: linkedSeller, superlikes: 0 });
        _postsBySeller[sellerTo].push(tokenId);
        return tokenId;
    }

    function getPost(uint256 tokenId) external view returns (address author, address sellerTo, address linkedSeller, uint8 superlikes) {
        Post memory p = _posts[tokenId];
        return (p.author, p.sellerTo, p.linkedSeller, p.superlikes);
    }

    function addSuperlike(uint256 tokenId) external returns (bool) {
        require(_posts[tokenId].author != address(0), "post does not exist");
        require(!hasSuperliked[tokenId][msg.sender], "already superliked");
        require(msg.sender != _posts[tokenId].author, "cannot like own post");
        hasSuperliked[tokenId][msg.sender] = true;
        _posts[tokenId].superlikes += 1;
        return true;
    }

    function getLoveDoCount(address seller) external view returns (uint8) {
        return uint8(_postsBySeller[seller].length);
    }
}
